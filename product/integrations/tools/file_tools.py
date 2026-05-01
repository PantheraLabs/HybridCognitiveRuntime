"""
File tracking tools for recording file edits and updating causal graph.

Handles:
- hcr_record_file_edit: Record a file edit event with detailed change information

k2.6 fixes:
- AST extraction runs in thread pool with 5s timeout (prevents blocking)
- Graceful fallback when AST parsing fails
- Updates dependency graph when imports change
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .base_tool import BaseMCPTool


class FileTools(BaseMCPTool):
    """File edit recording with timeout-protected AST extraction."""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Record a file edit event."""
        return await self._tool_record_file_edit(args)
    
    async def _tool_record_file_edit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Record a file edit with timeout-protected AST analysis (k2.6 fix)."""
        filepath = args.get("filepath")
        old_content = args.get("old_content", "")
        change_summary = args.get("change_summary", "")
        lines_added = args.get("lines_added", 0)
        lines_removed = args.get("lines_removed", 0)
        functions_changed = args.get("functions_changed", [])
        imports_changed = args.get("imports_changed", [])
        session_id = args.get("session_id")
        
        if not filepath:
            return self._error_response("filepath is required")
        
        engine = self._get_engine()
        if not engine:
            return {"content": "Engine not initialized", "recorded": False}
        
        from product.state_capture.file_watcher import FileWatcher, FileChange
        
        watcher = FileWatcher(self.responder.project_path if self.responder else ".")
        
        # Compute changes in thread pool to avoid blocking on AST/diff (k2.6 fix)
        change = None
        try:
            if old_content:
                change = await self._run_blocking(
                    lambda: watcher.capture_file_change(filepath, old_content),
                    timeout=5.0
                )
            else:
                change = FileChange(
                    path=filepath,
                    change_type='modified',
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    functions_changed=functions_changed,
                    imports_changed=imports_changed,
                    diff_summary=change_summary
                )
        except Exception as e:
            self.logger.warning(f"File change capture failed: {e}")
            # Fallback without AST analysis
            change = FileChange(
                path=filepath,
                change_type='modified',
                lines_added=lines_added,
                lines_removed=lines_removed,
                functions_changed=functions_changed,
                imports_changed=imports_changed,
                diff_summary=change_summary
            )
        
        # Create EngineEvent with detailed change info
        from src.engine_api import EngineEvent
        event = EngineEvent(
            event_type='file_edit',
            timestamp=datetime.now(),
            data={
                'path': filepath,
                'lines_added': change.lines_added if change else lines_added,
                'lines_removed': change.lines_removed if change else lines_removed,
                'functions_changed': change.functions_changed if change else functions_changed,
                'classes_changed': change.classes_changed if change else [],
                'imports_changed': change.imports_changed if change else imports_changed,
                'diff_summary': (change.diff_summary[:500] if change else change_summary),
                'change_summary': change_summary
            }
        )
        
        # Update engine state
        engine.update_from_environment(event)
        
        # Build response
        content = f"## File Edit Recorded\n\n"
        content += f"**File:** `{filepath}`\n"
        if change:
            content += f"**Change Type:** {change.change_type}\n"
            content += f"**Lines:** +{change.lines_added} / -{change.lines_removed}\n"
            if change.functions_changed:
                content += f"**Functions:** {', '.join(change.functions_changed)}\n"
            if change.imports_changed:
                content += f"**Imports:** {', '.join(change.imports_changed)}\n"
        else:
            content += f"**Lines:** +{lines_added} / -{lines_removed}\n"
            if functions_changed:
                content += f"**Functions:** {', '.join(functions_changed)}\n"
            if imports_changed:
                content += f"**Imports:** {', '.join(imports_changed)}\n"
        if change_summary:
            content += f"**Summary:** {change_summary}\n"
        
        content += "\nCausal graph and cognitive state updated."
        
        # Update dependency graph if imports changed
        if filepath.endswith('.py') and change and change.imports_changed:
            for imp in change.imports_changed:
                resolved = self._resolve_import_to_file(imp, engine)
                if resolved:
                    engine.dependency_graph.add_dependency(resolved, filepath)
            content += f"\nUpdated {len(change.imports_changed)} dependencies in causal graph."
        
        result = {
            "content": content,
            "recorded": True,
            "filepath": filepath,
            "change_type": change.change_type if change else 'modified',
            "lines_changed": (change.lines_added + change.lines_removed) if change else (lines_added + lines_removed)
        }
        
        # Record session snapshot if available
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, content, result)
        
        return result
    
    def _resolve_import_to_file(self, module_name: str, engine) -> Optional[str]:
        """Resolve a Python module import to a file path."""
        parts = module_name.split('.')
        project_path = getattr(engine, 'project_path', Path('.'))
        
        candidates = [
            Path(project_path) / f"{'/'.join(parts)}.py",
            Path(project_path) / '/'.join(parts) / "__init__.py"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate.relative_to(project_path))
        
        return None
