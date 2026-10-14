"""Plugin Inspection endpoints."""

from fastapi import APIRouter
from app.plugins.manifest import PluginManifest
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/plugins", tags=["Plugins"])


@router.get("", response_model=list[PluginManifest])
def list_plugins() -> list[PluginManifest]:
    """Lists all registered plugins and their capability manifests."""
    return workflow_manager.plugin_registry.list_manifests()
