from pathlib import Path

from pyc_hermes_agent.llm_gateway import resolve_llm_config, resolve_opencode_like_config


def test_resolved_config_has_first_class_copilot_provider() -> None:
    root = Path(__file__).resolve().parents[2]
    resolved = resolve_opencode_like_config(root)
    provider = resolved.providers["github-copilot"]
    assert provider.first_class is True
    assert any(method.id == "device-code" for method in provider.auth_methods)


def test_resolved_config_is_free_first_by_default() -> None:
    root = Path(__file__).resolve().parents[2]
    resolved = resolve_opencode_like_config(root)
    assert resolved.models[0].free is True
    assert resolved.default_model == resolved.models[0].id


def test_resolved_config_merges_custom_provider_models() -> None:
    raw = {
        "model": "demo/foo-free",
        "provider": {
            "demo": {
                "name": "Demo Provider",
                "options": {"baseURL": "http://127.0.0.1:9999/v1"},
                "models": {
                    "foo-free": {
                        "name": "Foo Free",
                        "tags": ["free", "tools"],
                        "supports_reasoning": True,
                    }
                },
            }
        },
    }
    resolved = resolve_llm_config(raw)
    assert "demo" in resolved.providers
    assert any(model.id == "demo/foo-free" for model in resolved.models)
    assert resolved.default_model == "demo/foo-free"


def test_resolved_config_preserves_model_overrides() -> None:
    raw = {
        "provider": {
            "opencode": {
                "models": {
                    "deepseek-v4-flash-free": {
                        "name": "DeepSeek V4 Flash Free Custom",
                        "variants": {
                            "high": {"reasoningEffort": "high"},
                        },
                    }
                }
            }
        }
    }
    resolved = resolve_llm_config(raw)
    model = next(model for model in resolved.models if model.id == "opencode/deepseek-v4-flash-free")
    assert model.name == "DeepSeek V4 Flash Free Custom"
    assert "high" in model.variants
