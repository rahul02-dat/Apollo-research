"""Guarded Plugin Execution Wrapper with Deadlines and Error Containment."""

import concurrent.futures
import logging
import time
from typing import Any, Callable
from app.config import settings
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


class PluginTimeoutError(PluginExecutionError):
    """Raised when plugin execution exceeds its configured deadline."""
    pass


class GuardedPluginExecutor:
    """Executes plugin capabilities with permission checks, error containment, execution deadlines, and auditing.

    NOTE ON SANDBOXING:
    In-process Python execution is not an OS security sandbox. Deadlines prevent unresponsive or slow plugins
    from blocking the research workflow or exhausting worker threads.
    """

    def __init__(
        self,
        policy_gate: PluginPolicyGate | None = None,
        default_timeout: float | None = None,
    ) -> None:
        self.policy_gate = policy_gate or PluginPolicyGate()
        self.default_timeout = default_timeout or settings.PLUGIN_EXECUTION_TIMEOUT_SECONDS

    def execute(
        self,
        plugin: Plugin,
        capability: str,
        operation: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        manifest = plugin.manifest
        self.policy_gate.authorize_capability(manifest, capability)

        execution_timeout = timeout or self.default_timeout
        start_time = time.perf_counter()
        logger.info(
            "Executing capability '%s' on plugin '%s' (v%s) [deadline: %.1fs]",
            capability, manifest.plugin_id, manifest.version, execution_timeout
        )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(operation, *args, **kwargs)
                result = future.result(timeout=execution_timeout)
                duration = time.perf_counter() - start_time
                logger.info("Capability '%s' on plugin '%s' succeeded in %.3fs", capability, manifest.plugin_id, duration)
                return result
        except concurrent.futures.TimeoutError as e:
            duration = time.perf_counter() - start_time
            logger.error("Capability '%s' on plugin '%s' timed out after %.3fs (deadline: %.1fs)", capability, manifest.plugin_id, duration, execution_timeout)
            raise PluginTimeoutError(manifest.plugin_id, capability, TimeoutError(f"Plugin execution exceeded deadline of {execution_timeout}s")) from e
        except PluginPolicyError:
            raise
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error("Capability '%s' on plugin '%s' failed after %.3fs: %s", capability, manifest.plugin_id, duration, e)
            raise PluginExecutionError(manifest.plugin_id, capability, e) from e

