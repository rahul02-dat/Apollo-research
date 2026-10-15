"""Plugin Policy and Permission verification."""

import logging
from typing import Any
from app.config import settings
from app.plugins.manifest import CURRENT_PLUGIN_API_VERSION, PluginManifest

logger = logging.getLogger(__name__)


class PluginPolicyError(Exception):
    """Raised when a plugin violates execution or authorization policy."""
    pass


class IncompatiblePluginError(PluginPolicyError):
    """Raised when a plugin API version does not match the host version."""
    pass


class UnauthorizedCapabilityError(PluginPolicyError):
    """Raised when a plugin attempts to execute an undeclared or ungranted capability."""
    pass


class PluginPolicyGate:
    """Enforces manifest validation, compatibility, and capability permissions.

    SECURITY BOUNDARY NOTICE:
    In-process Python plugins execute within the hosting process's OS security context and privileges.
    This execution layer is NOT an operating system security sandbox or container isolation boundary.
    Security and reliability rely on strict manifest schema validation, explicit capability authorization,
    runtime execution deadlines, and schema validation. Arbitrary untrusted user code must not be loaded in-process.
    """

    def __init__(
        self,
        allowed_api_versions: set[str] | None = None,
        fail_closed: bool | None = None,
    ) -> None:
        self.allowed_api_versions = allowed_api_versions or {CURRENT_PLUGIN_API_VERSION}
        self.fail_closed = fail_closed if fail_closed is not None else (settings.is_production or settings.FAIL_CLOSED_CAPABILITY_POLICY)
        self._granted_capabilities: dict[str, set[str]] = {}

    def validate_manifest(self, manifest: PluginManifest) -> None:
        """Validates plugin manifest schema and compatibility."""
        if not manifest.plugin_id or not manifest.plugin_id.strip():
            raise PluginPolicyError("Plugin manifest missing valid plugin_id.")

        if manifest.api_version not in self.allowed_api_versions:
            raise IncompatiblePluginError(
                f"Plugin '{manifest.plugin_id}' has incompatible API version '{manifest.api_version}' "
                f"(expected one of: {sorted(self.allowed_api_versions)})."
            )

    def grant_capabilities(self, plugin_id: str, capabilities: list[str]) -> None:
        """Explicitly grants capabilities to a registered plugin."""
        if plugin_id not in self._granted_capabilities:
            self._granted_capabilities[plugin_id] = set()
        self._granted_capabilities[plugin_id].update(capabilities)

    def authorize_capability(self, manifest: PluginManifest, capability: str) -> None:
        """Verifies that the requested capability is declared in the manifest and granted."""
        if capability not in manifest.capabilities:
            raise UnauthorizedCapabilityError(
                f"Plugin '{manifest.plugin_id}' does not declare capability '{capability}' in its manifest."
            )

        granted = self._granted_capabilities.get(manifest.plugin_id)
        if self.fail_closed:
            # Fail-closed policy (production default or explicitly configured): capability must be explicitly granted
            if not granted or capability not in granted:
                raise UnauthorizedCapabilityError(
                    f"Capability '{capability}' for plugin '{manifest.plugin_id}' is not granted under fail-closed capability policy."
                )
        else:
            # Development mode: if specific grants are defined, enforce them; otherwise allow declared capabilities
            if granted is not None and capability not in granted:
                raise UnauthorizedCapabilityError(
                    f"Capability '{capability}' was declared by '{manifest.plugin_id}' but not granted by policy."
                )

