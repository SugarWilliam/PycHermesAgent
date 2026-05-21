import json
import os
import socket
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from pyc_hermes_agent.contracts import ChatCompletionRequest, ChatMessage, ToolDefinition
from pyc_hermes_agent.llm_gateway import execute_chat, stream_chat as execute_stream, LLMChatRequest, LLMMessage
from pyc_hermes_agent.sidecar_api import create_http_server, invoke_chat_completion, stream_chat_completion
from pyc_hermes_agent import SidecarClient


class _FakeOpenAIHandler(BaseHTTPRequestHandler):
    last_request_payload = None
    last_request_headers = None
    request_payload_history = None
    request_headers_history = None
    stream_response_chunks = None
    response_sequence = None
    response_payload = {
        "id": "chatcmpl-demo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from fake model."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        _body = self.rfile.read(content_length)
        cls = self.__class__
        cls.last_request_payload = json.loads(_body.decode("utf-8"))
        cls.last_request_headers = {key.lower(): value for key, value in self.headers.items()}
        cls.request_payload_history.append(cls.last_request_payload)
        cls.request_headers_history.append(cls.last_request_headers)

        response_spec = cls.response_sequence.pop(0) if cls.response_sequence else {}
        status = response_spec.get("status", HTTPStatus.OK)
        if self.path.endswith("/chat/completions") and cls.last_request_payload.get("stream") is True and status == HTTPStatus.OK:
            chunks = response_spec.get("stream_chunks", self.stream_response_chunks or [])
            body_parts = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
            body_parts.append("data: [DONE]\n\n")
            body = "".join(body_parts).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = json.dumps(response_spec.get("body", self.response_payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return None


def _start_fake_openai_server():
    _FakeOpenAIHandler.last_request_payload = None
    _FakeOpenAIHandler.last_request_headers = None
    _FakeOpenAIHandler.request_payload_history = []
    _FakeOpenAIHandler.request_headers_history = []
    _FakeOpenAIHandler.stream_response_chunks = []
    _FakeOpenAIHandler.response_sequence = []
    _FakeOpenAIHandler.response_payload = {
        "id": "chatcmpl-demo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from fake model."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _make_runtime_root(
    tmp_path,
    base_url: str | None,
    *,
    provider_id: str = "openai-compatible",
    model_name: str = "demo-model",
    options: dict[str, str] | None = None,
):
    provider_options = dict(options or {})
    if base_url:
        provider_options.setdefault("baseURL", base_url)
    if provider_id == "openai-compatible":
        provider_options.setdefault("apiKey", "demo-token")
    config_text = json.dumps(
        {
            "model": f"{provider_id}/{model_name}",
            "provider": {
                provider_id: {
                    "options": provider_options,
                    "models": {
                        model_name: {
                            "name": "Demo Model",
                            "supports_reasoning": True,
                        }
                    },
                }
            },
        }
    )
    (tmp_path / "opencode.json").write_text(config_text, encoding="utf-8")
    return tmp_path


def _pick_unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_llm_gateway_executes_openai_compatible_chat(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        result = execute_chat(
            LLMChatRequest(
                model="openai-compatible/demo-model",
                messages=[LLMMessage(role="user", content="Say hello")],
            ),
            runtime_root,
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert result.provider_id == "openai-compatible"
    assert result.model == "openai-compatible/demo-model"
    assert result.content == "Hello from fake model."
    assert result.finish_reason == "stop"
    assert result.usage["total_tokens"] == 17


def test_llm_gateway_sends_tool_definitions_and_parses_tool_calls(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.response_payload = {
        "id": "chatcmpl-tools",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-demo",
                            "type": "function",
                            "function": {
                                "name": "echo_text",
                                "arguments": '{"text":"hello"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 18, "completion_tokens": 6, "total_tokens": 24},
    }
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        result = execute_chat(
            LLMChatRequest(
                model="openai-compatible/demo-model",
                messages=[LLMMessage(role="user", content="Say hello")],
                tools=[
                    ToolDefinition(
                        name="echo_text",
                        description="Echo text back to the caller.",
                        parameters={
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    )
                ],
            ),
            runtime_root,
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert _FakeOpenAIHandler.last_request_payload["tools"][0]["function"]["name"] == "echo_text"
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call-demo"
    assert result.tool_calls[0].name == "echo_text"
    assert result.tool_calls[0].arguments == '{"text":"hello"}'


def test_sidecar_python_api_invokes_chat_completion(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        response = invoke_chat_completion(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Say hello")],
            ),
            root=runtime_root,
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert response["provider_id"] == "openai-compatible"
    assert response["content"] == "Hello from fake model."


def test_sidecar_http_transport_invokes_chat_completion(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")
    sidecar_server = create_http_server(port=0, root=runtime_root)
    sidecar_thread = threading.Thread(target=sidecar_server.serve_forever, daemon=True)
    sidecar_thread.start()
    base_url = f"http://127.0.0.1:{sidecar_server.server_address[1]}"

    try:
        client = SidecarClient(base_url=base_url)
        response = client.invoke_chat_completion(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Say hello")],
            )
        )
    finally:
        sidecar_server.shutdown()
        sidecar_server.server_close()
        sidecar_thread.join(timeout=5)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert response["provider_id"] == "openai-compatible"
    assert response["content"] == "Hello from fake model."


def test_sidecar_http_transport_returns_error_payload_for_chat_failures(tmp_path) -> None:
    sidecar_server = create_http_server(port=0, root=tmp_path)
    sidecar_thread = threading.Thread(target=sidecar_server.serve_forever, daemon=True)
    sidecar_thread.start()
    base_url = f"http://127.0.0.1:{sidecar_server.server_address[1]}"

    try:
        client = SidecarClient(base_url=base_url)
        response = client.invoke_chat_completion(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Say hello")],
            )
        )
    finally:
        sidecar_server.shutdown()
        sidecar_server.server_close()
        sidecar_thread.join(timeout=5)

    assert response["status"] == "error"
    assert response["error"]["code"] == "LLM_CHAT_FAILED"
    assert response["error"]["domain"] == "llm"


def test_llm_gateway_executes_github_copilot_chat(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    runtime_root = _make_runtime_root(
        tmp_path,
        f"http://127.0.0.1:{provider_server.server_address[1]}/v1",
        provider_id="github-copilot",
        model_name="gpt-4.1",
    )

    try:
        with patch.dict(
            os.environ,
            {
                "COPILOT_GITHUB_TOKEN": "",
                "GH_TOKEN": "gho_demo-token",
                "GITHUB_TOKEN": "",
            },
            clear=False,
        ):
            response = invoke_chat_completion(
                ChatCompletionRequest(
                    model="github-copilot/gpt-4.1",
                    messages=[ChatMessage(role="user", content="Say hello")],
                ),
                root=runtime_root,
            )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert response["provider_id"] == "github-copilot"
    assert response["content"] == "Hello from fake model."
    assert _FakeOpenAIHandler.last_request_payload["model"] == "gpt-4.1"
    assert _FakeOpenAIHandler.last_request_headers["authorization"] == "Bearer gho_demo-token"
    assert _FakeOpenAIHandler.last_request_headers["editor-version"] == "vscode/1.104.1"
    assert _FakeOpenAIHandler.last_request_headers["copilot-integration-id"] == "vscode-chat"
    assert _FakeOpenAIHandler.last_request_headers["openai-intent"] == "conversation-edits"
    assert _FakeOpenAIHandler.last_request_headers["x-initiator"] == "agent"


def test_llm_gateway_refreshes_github_copilot_credentials_after_401(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.response_sequence = [
        {
            "status": HTTPStatus.UNAUTHORIZED,
            "body": {"error": {"message": "expired"}},
        },
        {
            "status": HTTPStatus.OK,
            "body": _FakeOpenAIHandler.response_payload,
        },
    ]
    runtime_root = _make_runtime_root(
        tmp_path,
        f"http://127.0.0.1:{provider_server.server_address[1]}/v1",
        provider_id="github-copilot",
        model_name="gpt-4.1",
    )

    try:
        with patch(
            "pyc_hermes_agent.llm_gateway.runtime._resolve_github_copilot_token",
            side_effect=["gho_first-token", "gho_second-token"],
        ):
            result = execute_chat(
                LLMChatRequest(
                    model="github-copilot/gpt-4.1",
                    messages=[LLMMessage(role="user", content="Say hello")],
                ),
                runtime_root,
            )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert result.provider_id == "github-copilot"
    assert result.content == "Hello from fake model."
    assert len(_FakeOpenAIHandler.request_headers_history) == 2
    assert _FakeOpenAIHandler.request_headers_history[0]["authorization"] == "Bearer gho_first-token"
    assert _FakeOpenAIHandler.request_headers_history[1]["authorization"] == "Bearer gho_second-token"


def test_llm_gateway_rejects_classic_pat_for_github_copilot(tmp_path) -> None:
    runtime_root = _make_runtime_root(
        tmp_path,
        "http://127.0.0.1:9/v1",
        provider_id="github-copilot",
        model_name="gpt-4.1",
        options={"apiKey": "ghp_legacy-token"},
    )

    response = invoke_chat_completion(
        ChatCompletionRequest(
            model="github-copilot/gpt-4.1",
            messages=[ChatMessage(role="user", content="Say hello")],
        ),
        root=runtime_root,
    )

    assert response["status"] == "error"
    assert response["error"]["code"] == "LLM_CHAT_FAILED"
    assert response["error"]["domain"] == "llm"
    assert "does not support classic GitHub PATs" in response["error"]["message"]


def test_sidecar_process_smoke_llm_chat(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")
    port = _pick_unused_port()
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else src_path + os.pathsep + env["PYTHONPATH"]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pyc_hermes_agent.sidecar_api.http_server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--root",
            str(runtime_root),
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        for _ in range(20):
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1):
                    break
            except Exception:
                time.sleep(0.25)
        else:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            raise AssertionError(f"Sidecar process did not start in time. stderr={stderr}")

        request = Request(
            f"http://127.0.0.1:{port}/llm/chat",
            data=json.dumps(
                {
                    "model": "openai-compatible/demo-model",
                    "messages": [{"role": "user", "content": "Say hello"}],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response_handle:
            payload = json.loads(response_handle.read().decode("utf-8"))
    finally:
        process.terminate()
        process.wait(timeout=10)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert payload["provider_id"] == "openai-compatible"
    assert payload["content"] == "Hello from fake model."


def test_llm_gateway_streams_openai_compatible_chat(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.stream_response_chunks = [
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
        },
    ]
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        chunks = list(
            execute_stream(
                LLMChatRequest(
                    model="openai-compatible/demo-model",
                    messages=[LLMMessage(role="user", content="Say hello")],
                ),
                runtime_root,
            )
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert _FakeOpenAIHandler.last_request_payload["stream"] is True
    assert chunks[0].delta == "Hello"
    assert chunks[1].delta == " world"
    assert chunks[-1].event == "done"
    assert chunks[-1].content == "Hello world"


def test_llm_gateway_streams_tool_call_formation(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.stream_response_chunks = [
        {
            "id": "chatcmpl-stream-tool",
            "model": "openai-compatible/demo-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call-demo",
                                "type": "function",
                                "function": {"name": "echo_text", "arguments": '{"text":"he'},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-stream-tool",
            "model": "openai-compatible/demo-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"arguments": 'llo"}'},
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        },
    ]
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        chunks = list(
            execute_stream(
                LLMChatRequest(
                    model="openai-compatible/demo-model",
                    messages=[LLMMessage(role="user", content="Call the tool")],
                ),
                runtime_root,
            )
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert chunks[0].tool_calls[0].name == "echo_text"
    assert chunks[0].tool_calls[0].arguments == '{"text":"he'
    assert chunks[1].tool_calls[0].arguments == '{"text":"hello"}'
    assert chunks[-1].event == "done"
    assert chunks[-1].tool_calls[0].name == "echo_text"


def test_sidecar_python_api_streams_chat_completion(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.stream_response_chunks = [
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
        },
    ]
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")

    try:
        response = list(
            stream_chat_completion(
                ChatCompletionRequest(
                    model="openai-compatible/demo-model",
                    messages=[ChatMessage(role="user", content="Say hello")],
                ),
                root=runtime_root,
            )
        )
    finally:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert response[0]["event"] == "delta"
    assert response[0]["delta"] == "Hello"
    assert response[-1]["event"] == "done"
    assert response[-1]["content"] == "Hello world"


def test_sidecar_http_transport_streams_chat_completion(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.stream_response_chunks = [
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
        },
    ]
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")
    sidecar_server = create_http_server(port=0, root=runtime_root)
    sidecar_thread = threading.Thread(target=sidecar_server.serve_forever, daemon=True)
    sidecar_thread.start()
    base_url = f"http://127.0.0.1:{sidecar_server.server_address[1]}"

    try:
        request = Request(
            f"{base_url}/llm/chat/stream",
            data=json.dumps(
                {
                    "model": "openai-compatible/demo-model",
                    "messages": [{"role": "user", "content": "Say hello"}],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response_handle:
            payload = response_handle.read().decode("utf-8")
    finally:
        sidecar_server.shutdown()
        sidecar_server.server_close()
        sidecar_thread.join(timeout=5)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert '"event": "delta"' in payload
    assert '"delta": "Hello"' in payload
    assert '"event": "done"' in payload


def test_sidecar_client_supports_streaming_chat_over_http(tmp_path) -> None:
    provider_server, provider_thread = _start_fake_openai_server()
    _FakeOpenAIHandler.stream_response_chunks = [
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-stream-demo",
            "model": "openai-compatible/demo-model",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
        },
    ]
    runtime_root = _make_runtime_root(tmp_path, f"http://127.0.0.1:{provider_server.server_address[1]}/v1")
    sidecar_server = create_http_server(port=0, root=runtime_root)
    sidecar_thread = threading.Thread(target=sidecar_server.serve_forever, daemon=True)
    sidecar_thread.start()
    base_url = f"http://127.0.0.1:{sidecar_server.server_address[1]}"

    try:
        client = SidecarClient(base_url=base_url)
        chunks = list(
            client.stream_chat_completion(
                ChatCompletionRequest(
                    model="openai-compatible/demo-model",
                    messages=[ChatMessage(role="user", content="Say hello")],
                )
            )
        )
    finally:
        sidecar_server.shutdown()
        sidecar_server.server_close()
        sidecar_thread.join(timeout=5)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

    assert chunks[0]["event"] == "delta"
    assert chunks[-1]["event"] == "done"
    assert chunks[-1]["content"] == "Hello world"
