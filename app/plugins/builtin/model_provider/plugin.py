"""Built-in Model Provider Plugins: Local Ollama (gemma4) and Deterministic Mock."""

import json
import logging
from typing import Any
import httpx
from pydantic import BaseModel
from app.config import settings
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class OllamaModelProvider:
    """Invokes local Ollama server (e.g. gemma4:latest)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds

        self.manifest = PluginManifest(
            plugin_id="ollama",
            display_name=f"Ollama Local LLM ({self.model})",
            version="1.0.0",
            api_version="1.0",
            plugin_type="model_provider",
            capabilities=["model.text.generate", "model.structured.generate"],
            required_permissions=["network.local.ollama"],
            config_schema={
                "base_url": {"type": "string"},
                "model": {"type": "string"},
            },
            enabled_by_default=True,
        )

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Invokes Ollama generate API."""
        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return str(data.get("response", "")).strip()
        except Exception as e:
            logger.error("Ollama generate failed (%s): %s", self.model, e)
            raise RuntimeError(f"Ollama generation failed for model '{self.model}': {e}") from e

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
    ) -> BaseModel:
        """Invokes Ollama with JSON format constraint and parses Pydantic model."""
        url = f"{self.base_url}/api/generate"
        json_schema_prompt = (
            f"{prompt}\n\nYou MUST reply ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": json_schema_prompt,
            "format": "json",
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_json = str(data.get("response", "")).strip()
                parsed = json.loads(raw_json)
                return schema.model_validate(parsed)
        except Exception as e:
            logger.warning("Ollama structured generation failed, attempting schema repair: %s", e)
            raise RuntimeError(f"Failed to generate structured response from Ollama: {e}") from e


class MockModelProvider:
    """Deterministic, offline mock model provider for reproducible testing."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="mock",
            display_name="Deterministic Mock LLM Provider",
            version="1.0.0",
            api_version="1.0",
            plugin_type="model_provider",
            capabilities=["model.text.generate", "model.structured.generate"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"[Mock Analysis] Based on verified evidence: {prompt[:120]}..."

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
    ) -> BaseModel:
        # Return default instance or minimal valid data for the schema
        sample_dict: dict[str, Any] = {}
        for field_name, field_info in schema.model_fields.items():
            annotation = field_info.annotation
            if annotation == str or annotation == (str | None):
                sample_dict[field_name] = f"Mock {field_name}"
            elif annotation == list or str(annotation).startswith("list"):
                sample_dict[field_name] = []
            elif annotation == int:
                sample_dict[field_name] = 1
            elif annotation == bool:
                sample_dict[field_name] = True
            elif annotation == dict or str(annotation).startswith("dict"):
                sample_dict[field_name] = {}
        return schema.model_validate(sample_dict)


def create_ollama_plugin() -> OllamaModelProvider:
    return OllamaModelProvider()


def create_mock_plugin() -> MockModelProvider:
    return MockModelProvider()
