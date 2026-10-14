"""Plugin Registry and Discovery management."""

import importlib.metadata
import logging
from typing import Any, TypeVar, cast
from app.plugins.contracts import (
    DocumentExtractor,
    EvidenceValidator,
    FinancialAnalytics,
    ModelProvider,
    Plugin,
    ReportExporter,
    SourceConnector,
    SynthesisStrategy,
)
from app.plugins.execution import GuardedPluginExecutor
from app.plugins.manifest import PluginManifest, PluginType
from app.plugins.policy import PluginPolicyError, PluginPolicyGate

logger = logging.getLogger(__name__)

TPlugin = TypeVar("TPlugin", bound=Plugin)


class PluginRegistrationError(PluginPolicyError):
    """Raised when registering an invalid or duplicate plugin."""
    pass


class PluginRegistry:
    """Central registry and life-cycle manager for Apollo plugins."""

    def __init__(
        self,
        policy_gate: PluginPolicyGate | None = None,
        executor: GuardedPluginExecutor | None = None,
    ) -> None:
        self.policy_gate = policy_gate or PluginPolicyGate()
        self.executor = executor or GuardedPluginExecutor(self.policy_gate)
        self._plugins: dict[str, Plugin] = {}
        self._enabled_status: dict[str, bool] = {}

    def register(self, plugin: Plugin, overwrite: bool = False) -> None:
        """Validates and registers a plugin instance."""
        if not hasattr(plugin, "manifest") or not isinstance(plugin.manifest, PluginManifest):
            raise PluginRegistrationError("Plugin does not expose a valid PluginManifest.")

        manifest = plugin.manifest
        self.policy_gate.validate_manifest(manifest)

        if manifest.plugin_id in self._plugins and not overwrite:
            raise PluginRegistrationError(
                f"Duplicate plugin registration: plugin_id '{manifest.plugin_id}' already registered."
            )

        self._validate_contract_type(plugin, manifest.plugin_type)
        self._plugins[manifest.plugin_id] = plugin
        self._enabled_status[manifest.plugin_id] = manifest.enabled_by_default
        logger.info("Registered plugin '%s' (type: %s, version: %s)", manifest.plugin_id, manifest.plugin_type, manifest.version)

    def _validate_contract_type(self, plugin: Plugin, plugin_type: PluginType) -> None:
        expected_methods = {
            "source_connector": ["resolve_issuer", "search", "fetch", "get_company_facts"],
            "document_extractor": ["extract"],
            "evidence_validator": ["validate"],
            "financial_analytics": ["compute_metrics"],
            "synthesis_strategy": ["synthesize_section"],
            "model_provider": ["generate", "generate_structured"],
            "report_exporter": ["export"],
        }
        for method in expected_methods.get(plugin_type, []):
            if not callable(getattr(plugin, method, None)):
                raise PluginRegistrationError(
                    f"Plugin '{plugin.manifest.plugin_id}' of type '{plugin_type}' missing required method '{method}'."
                )

    def get_plugin(self, plugin_id: str) -> Plugin:
        if plugin_id not in self._plugins:
            raise KeyError(f"Plugin '{plugin_id}' not found in registry.")
        if not self.is_enabled(plugin_id):
            raise PluginPolicyError(f"Plugin '{plugin_id}' is disabled.")
        return self._plugins[plugin_id]

    def get_typed_plugin(self, plugin_id: str, expected_type: type[TPlugin]) -> TPlugin:
        plugin = self.get_plugin(plugin_id)
        if not isinstance(plugin, expected_type):
            raise TypeError(f"Plugin '{plugin_id}' is not an instance of {expected_type.__name__}.")
        return cast(TPlugin, plugin)

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        return [
            p for p in self._plugins.values()
            if p.manifest.plugin_type == plugin_type and self.is_enabled(p.manifest.plugin_id)
        ]

    def is_enabled(self, plugin_id: str) -> bool:
        return self._enabled_status.get(plugin_id, False)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        if plugin_id not in self._plugins:
            raise KeyError(f"Plugin '{plugin_id}' not found.")
        self._enabled_status[plugin_id] = enabled

    def list_manifests(self) -> list[PluginManifest]:
        return [p.manifest for p in self._plugins.values()]

    def discover_entrypoints(self) -> None:
        """Discovers and registers plugins exposed via Python entry points."""
        groups = [
            "apollo.source_plugins",
            "apollo.extractor_plugins",
            "apollo.validator_plugins",
            "apollo.synthesis_plugins",
            "apollo.model_plugins",
            "apollo.exporter_plugins",
        ]
        for group in groups:
            try:
                eps = importlib.metadata.entry_points(group=group)
                for ep in eps:
                    try:
                        factory = ep.load()
                        plugin = factory()
                        self.register(plugin, overwrite=True)
                    except Exception as e:
                        logger.warning("Failed loading entry point '%s' in group '%s': %s", ep.name, group, e)
            except Exception as e:
                logger.warning("Could not inspect entry points for group '%s': %s", group, e)
