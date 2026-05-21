"""Resolver for built-in and config-defined LLM gateway state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from pyc_hermes_agent.llm_gateway.catalog import BUILTIN_MODELS, BUILTIN_PROVIDERS
from pyc_hermes_agent.llm_gateway.types import ModelSpec, ModelVariantSpec, ProviderConfig, ProviderSpec, ResolvedLLMConfig


def sort_models_free_first(models: Iterable[ModelSpec]) -> list[ModelSpec]:
    return sorted(
        models,
        key=lambda model: (
            not model.free,
            model.featured_rank,
            model.name.lower(),
        ),
    )


def resolve_llm_config(raw_config: Dict[str, Any], config_path: Optional[Path] = None) -> ResolvedLLMConfig:
    providers = {provider_id: deepcopy(spec) for provider_id, spec in BUILTIN_PROVIDERS.items()}
    models = {model.id: deepcopy(model) for model in BUILTIN_MODELS}
    provider_configs: Dict[str, ProviderConfig] = {}

    for provider_id, provider_raw in raw_config.get("provider", {}).items():
        provider_config = ProviderConfig(
            provider_id=provider_id,
            name=provider_raw.get("name"),
            npm=provider_raw.get("npm"),
            base_url=provider_raw.get("options", {}).get("baseURL") or provider_raw.get("options", {}).get("base_url"),
            headers=deepcopy(provider_raw.get("options", {}).get("headers", {})),
            options=deepcopy(provider_raw.get("options", {})),
            model_overrides=deepcopy(provider_raw.get("models", {})),
        )
        provider_configs[provider_id] = provider_config

        if provider_id not in providers:
            providers[provider_id] = ProviderSpec(
                id=provider_id,
                name=provider_config.name or provider_id,
                first_class=False,
                source="config",
            )
        elif provider_config.name:
            providers[provider_id] = replace(providers[provider_id], name=provider_config.name)

        for model_id, model_raw in provider_config.model_overrides.items():
            full_id = f"{provider_id}/{model_id}"
            model = models.get(full_id)
            if model is None:
                model = ModelSpec(
                    id=full_id,
                    provider_id=provider_id,
                    model_id=model_id,
                    name=model_raw.get("name", model_id),
                    free=_infer_free(model_id, model_raw),
                    supports_tools=bool(model_raw.get("supports_tools", True)),
                    supports_vision=bool(model_raw.get("supports_vision", False)),
                    supports_reasoning=bool(model_raw.get("supports_reasoning", False)),
                    featured_rank=1000,
                    source="config",
                )

            tags = list(dict.fromkeys([*model.tags, *model_raw.get("tags", [])]))
            variants = deepcopy(model.variants)
            for variant_id, variant_raw in model_raw.get("variants", {}).items():
                variants[variant_id] = ModelVariantSpec(
                    id=variant_id,
                    options=deepcopy(variant_raw),
                    disabled=bool(variant_raw.get("disabled", False)),
                )

            models[full_id] = replace(
                model,
                name=model_raw.get("name", model.name),
                tags=tags,
                free=bool(model_raw.get("free", model.free or _infer_free(model_raw.get("name", model.name), model_raw))),
                supports_tools=bool(model_raw.get("supports_tools", model.supports_tools)),
                supports_vision=bool(model_raw.get("supports_vision", model.supports_vision)),
                supports_reasoning=bool(model_raw.get("supports_reasoning", model.supports_reasoning)),
                options={**model.options, **deepcopy(model_raw.get("options", {}))},
                variants=variants,
                disabled=bool(model_raw.get("disabled", model.disabled)),
                source=model.source if model.source != "builtin" else "builtin+config",
            )

    sorted_models = sort_models_free_first(model for model in models.values() if not model.disabled)
    default_model = raw_config.get("model") or (sorted_models[0].id if sorted_models else "")
    small_model = raw_config.get("small_model")
    if small_model is None:
        default_provider_id = default_model.split("/", 1)[0] if "/" in default_model else None
        if default_provider_id and default_provider_id in providers:
            small_model = providers[default_provider_id].default_small_model_id

    return ResolvedLLMConfig(
        config_path=config_path,
        raw_config=deepcopy(raw_config),
        providers=providers,
        provider_configs=provider_configs,
        models=sorted_models,
        default_model=default_model,
        small_model=small_model,
        free_first=True,
    )


def _infer_free(model_name: str, model_raw: Dict[str, Any]) -> bool:
    if "free" in model_raw:
        return bool(model_raw["free"])
    tags = {tag.lower() for tag in model_raw.get("tags", [])}
    return "free" in tags or "free" in model_name.lower()
