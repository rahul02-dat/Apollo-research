"""Built-in Apollo Plugins."""

from app.plugins.builtin.evidence_validator.plugin import create_plugin as create_validator_plugin
from app.plugins.builtin.html_extractor.plugin import create_plugin as create_html_plugin
from app.plugins.builtin.model_provider.plugin import create_mock_plugin, create_ollama_plugin
from app.plugins.builtin.pdf_exporter.plugin import create_plugin as create_pdf_plugin
from app.plugins.builtin.sec_source.plugin import create_plugin as create_sec_plugin
from app.plugins.builtin.synthesis_strategy.plugin import create_plugin as create_synthesis_plugin
from app.plugins.builtin.xbrl_extractor.plugin import create_plugin as create_xbrl_plugin
from app.plugins.registry import PluginRegistry


def register_builtin_plugins(registry: PluginRegistry) -> None:
    """Registers the core built-in plugins into the registry."""
    registry.register(create_sec_plugin(), overwrite=True)
    registry.register(create_html_plugin(), overwrite=True)
    registry.register(create_xbrl_plugin(), overwrite=True)
    registry.register(create_validator_plugin(), overwrite=True)
    registry.register(create_synthesis_plugin(), overwrite=True)
    registry.register(create_ollama_plugin(), overwrite=True)
    registry.register(create_mock_plugin(), overwrite=True)
    registry.register(create_pdf_plugin(), overwrite=True)
