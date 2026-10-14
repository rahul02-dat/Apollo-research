"""Apollo Plugin Architecture."""

from app.plugins.manifest import PluginManifest, PluginType, CURRENT_PLUGIN_API_VERSION
from app.plugins.contracts import (
    Plugin,
    SourceConnector,
    DocumentExtractor,
    EvidenceValidator,
    FinancialAnalytics,
    SynthesisStrategy,
    ModelProvider,
    ReportExporter,
)
from app.plugins.policy import (
    PluginPolicyGate,
    PluginPolicyError,
    IncompatiblePluginError,
    UnauthorizedCapabilityError,
)
from app.plugins.execution import GuardedPluginExecutor, PluginExecutionError
from app.plugins.registry import PluginRegistry, PluginRegistrationError

__all__ = [
    "PluginManifest",
    "PluginType",
    "CURRENT_PLUGIN_API_VERSION",
    "Plugin",
    "SourceConnector",
    "DocumentExtractor",
    "EvidenceValidator",
    "FinancialAnalytics",
    "SynthesisStrategy",
    "ModelProvider",
    "ReportExporter",
    "PluginPolicyGate",
    "PluginPolicyError",
    "IncompatiblePluginError",
    "UnauthorizedCapabilityError",
    "GuardedPluginExecutor",
    "PluginExecutionError",
    "PluginRegistry",
    "PluginRegistrationError",
]
