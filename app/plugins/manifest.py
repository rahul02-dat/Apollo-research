"""Plugin Manifest and Capability definitions."""

from typing import Any, Literal
from pydantic import BaseModel, Field

PluginType = Literal[
    "source_connector",
    "document_extractor",
    "evidence_validator",
    "financial_analytics",
    "synthesis_strategy",
    "model_provider",
    "report_exporter",
]

CURRENT_PLUGIN_API_VERSION = "1.0"


class PluginManifest(BaseModel):
    plugin_id: str
    display_name: str
    version: str
    api_version: str = CURRENT_PLUGIN_API_VERSION
    plugin_type: PluginType
    capabilities: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    enabled_by_default: bool = True
