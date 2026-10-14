"""Guarded Plugin Execution Wrapper."""

import logging
import time
from typing import Any, Callable
from app.plugins.contracts import Plugin
from app.plugins.policy import PluginPolicyGate, PluginPolicyError

logger = logging.getLogger(__name__)


class PluginExecutionError(Exception):
    """Raised when plugin execution fails or returns malformed results."""
    def __init__(self, plugin_id: str, capability: str, original_error: Exception) -> None:
        super().__init__(f"Plugin '{plugin_id}' failed executing '{capability}': {original_error}")
        self.plugin_id = plugin_id
        self.capability = capability
        self.original_error = original_error


class GuardedPluginExecutor:
    """Executes plugin capabilities with permission checks, error containment, and auditing."""

    def __init__(self, policy_gate: PluginPolicyGate | None = None) -> None:
        self.policy_gate = policy_gate or PluginPolicyGate()

    def execute(
        self,
        plugin: Plugin,
        capability: str,
        operation: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        manifest = plugin.manifest
        self.policy_gate.authorize_capability(manifest, capability)

        start_time = time.perf_counter()
        logger.info("Executing capability '%s' on plugin '%s' (v%s)", capability, manifest.plugin_id, manifest.version)

        try:
            result = operation(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.info("Capability '%s' on plugin '%s' succeeded in %.3fs", capability, manifest.plugin_id, duration)
            return result
        except PluginPolicyError:
            raise
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error("Capability '%s' on plugin '%s' failed after %.3fs: %s", capability, manifest.plugin_id, duration, e)
            raise PluginExecutionError(manifest.plugin_id, capability, e) from e
