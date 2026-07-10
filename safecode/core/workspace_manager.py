"""Workspace lifecycle management for isolated SafeCode sessions."""

from pathlib import Path
import shutil
import tempfile
import uuid


class WorkspaceManager:
    """Create and clean up temporary workspaces copied from task templates."""

    def __init__(self) -> None:
        self.workspace_root: Path | None = None
        self._keep = False

    def setup(self, template_path: Path, keep: bool = False) -> Path:
        template = Path(template_path)
        if not template.exists():
            raise FileNotFoundError(f"Workspace template does not exist: {template}")
        if not template.is_dir():
            raise NotADirectoryError(f"Workspace template is not a directory: {template}")

        workspace = Path(tempfile.gettempdir()) / f"safecode-session-{uuid.uuid4()}"
        shutil.copytree(template, workspace)
        self.workspace_root = workspace
        self._keep = keep
        return workspace

    def cleanup(self) -> None:
        if self.workspace_root is None:
            return
        if self._keep:
            return

        shutil.rmtree(self.workspace_root, ignore_errors=True)
        self.workspace_root = None