"""Built-in provider and model catalog for the minimum LLM gateway."""

from __future__ import annotations

from pyc_hermes_agent.llm_gateway.types import AuthMethodSpec, ModelSpec, ProviderSpec


BUILTIN_PROVIDERS: dict[str, ProviderSpec] = {
    "github-copilot": ProviderSpec(
        id="github-copilot",
        name="GitHub Copilot",
        auth_methods=[
            AuthMethodSpec(id="device-code", label="Device Code", kind="oauth", enterprise_supported=True),
            AuthMethodSpec(id="api-key", label="Access Token", kind="token", enterprise_supported=True),
        ],
        default_model_id="github-copilot/gpt-4.1",
        default_small_model_id="github-copilot/gpt-4o-mini",
        first_class=True,
        source="builtin",
    ),
    "opencode": ProviderSpec(
        id="opencode",
        name="OpenCode-style Catalog",
        auth_methods=[AuthMethodSpec(id="api-key", label="API Key", kind="api_key")],
        default_model_id="opencode/deepseek-v4-flash-free",
        default_small_model_id="opencode/deepseek-v4-flash-free",
        first_class=True,
        free_first=True,
        source="builtin",
    ),
    "openrouter": ProviderSpec(
        id="openrouter",
        name="OpenRouter",
        auth_methods=[AuthMethodSpec(id="api-key", label="API Key", kind="api_key")],
        source="builtin",
    ),
    "openai-compatible": ProviderSpec(
        id="openai-compatible",
        name="OpenAI Compatible",
        auth_methods=[AuthMethodSpec(id="api-key", label="API Key", kind="api_key")],
        source="builtin",
    ),
    "ollama": ProviderSpec(
        id="ollama",
        name="Ollama",
        auth_methods=[AuthMethodSpec(id="local", label="Local Runtime", kind="local")],
        source="builtin",
    ),
    "lmstudio": ProviderSpec(
        id="lmstudio",
        name="LM Studio",
        auth_methods=[AuthMethodSpec(id="local", label="Local Runtime", kind="local")],
        source="builtin",
    ),
}


BUILTIN_MODELS: list[ModelSpec] = [
    ModelSpec(
        id="github-copilot/gpt-4.1",
        provider_id="github-copilot",
        model_id="gpt-4.1",
        name="GPT-4.1",
        tags=["tools", "reasoning"],
        free=False,
        supports_tools=True,
        supports_reasoning=True,
        featured_rank=10,
    ),
    ModelSpec(
        id="github-copilot/gpt-4o",
        provider_id="github-copilot",
        model_id="gpt-4o",
        name="GPT-4o",
        tags=["tools", "reasoning", "fast"],
        free=False,
        supports_tools=True,
        supports_reasoning=True,
        featured_rank=11,
    ),
    ModelSpec(
        id="github-copilot/gpt-4o-mini",
        provider_id="github-copilot",
        model_id="gpt-4o-mini",
        name="GPT-4o Mini",
        tags=["fast", "tools"],
        free=False,
        supports_tools=True,
        supports_reasoning=False,
        featured_rank=12,
    ),
]
