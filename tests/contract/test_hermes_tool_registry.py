from pyc_hermes_agent.contracts import HermesToolDescriptor, HermesToolsSnapshot, ToolCall
from pyc_hermes_agent.hermes_engine import ToolRegistry


def test_tool_registry_bootstraps_from_hermes_tool_snapshot() -> None:
    snapshot = HermesToolsSnapshot(
        tools=[
            HermesToolDescriptor(
                id="demo_tool",
                name="demo_tool",
                path="tools/demo_tool.py",
                source="builtin",
                toolset_hints=["safe"],
                requires_env=["DEMO_TOKEN"],
                registration_style="registry.register",
                registered=True,
            )
        ]
    )

    registry = ToolRegistry.from_snapshot(snapshot)

    assert registry.has_tool("demo_tool") is True
    descriptors = registry.list_descriptors()
    assert descriptors[0].toolset_hints == ["safe"]
    assert descriptors[0].requires_env == ["DEMO_TOKEN"]
    openai_tools = registry.list_openai_tools()
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "demo_tool"
    assert openai_tools[0]["function"]["parameters"]["type"] == "object"


def test_tool_registry_dispatches_openai_style_tool_calls() -> None:
    registry = ToolRegistry()
    registry.register_function(
        "echo_text",
        lambda args: {"echo": args["text"]},
        description="Echo text back to the caller.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    result = registry.dispatch(
        {
            "id": "call-123",
            "type": "function",
            "function": {
                "name": "echo_text",
                "arguments": {"text": "hello"},
            },
        }
    )

    assert result.tool_call_id == "call-123"
    assert result.name == "echo_text"
    assert result.is_error is False
    assert result.structured_content == {"echo": "hello"}
    assert result.content == '{"echo": "hello"}'


def test_tool_registry_reports_invalid_json_arguments_as_tool_error() -> None:
    registry = ToolRegistry()
    registry.register_function("echo_text", lambda args: args)

    result = registry.dispatch(ToolCall(id="call-456", name="echo_text", arguments='["bad"]'))

    assert result.tool_call_id == "call-456"
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "TOOL_ARGUMENTS_INVALID"
