"""
State Persistence for "Resume Without Re-Explaining"

Advanced state persistence with:
- Causal graph persistence
- Cross-project state management
- Versioned state history (git-like)
- State compression
- Encrypted storage for enterprise

Saves and loads developer cognitive state to/from disk.
State stored in .hcr/ directory at project root.
"""

import os
import json
import gzip
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import threading
import shutil


@dataclass
class StateVersion:
    """Git-like version for cognitive states"""
    hash: str
    timestamp: str
    message: str
    parent_hashes: List[str]
    state_size_bytes: int


@dataclass
class CausalGraphState:
    """Serializable causal graph for persistence"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class DevStatePersistence:
    """
    Handles saving and loading developer cognitive state.
    
    Features:
    - Causal graph persistence
    - Cross-project state management
    - Versioned state history
    - State compression
    - Encrypted storage (enterprise)
    """
    
    def __init__(self, project_path: str, enable_compression: bool = True, encryption_key: Optional[str] = None):
        self.project_path = Path(project_path)
        self.hcr_dir = self.project_path / ".hcr"
        self.state_file = self.hcr_dir / "session_state.json"
        self.history_dir = self.hcr_dir / "history"
        self.causal_dir = self.hcr_dir / "causal_graphs"
        self.versions_file = self.hcr_dir / "versions.json"
        self.lock = threading.Lock()
        
        # Feature flags
        self.enable_compression = enable_compression
        self.encryption_key = encryption_key
        
        # Ensure directories
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Ensure .hcr directories exist"""
        self.hcr_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
        self.causal_dir.mkdir(exist_ok=True)
        
    def _compute_state_hash(self, state: Dict[str, Any]) -> str:
        """Compute hash for state versioning"""
        state_json = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()[:16]
    
    def _compress_state(self, state: Dict[str, Any]) -> bytes:
        """Compress state for efficient storage"""
        json_bytes = json.dumps(state).encode()
        return gzip.compress(json_bytes) if self.enable_compression else json_bytes
    
    def _decompress_state(self, data: bytes) -> Dict[str, Any]:
        """Decompress state from storage"""
        try:
            decompressed = gzip.decompress(data)
            return json.loads(decompressed.decode())
        except:
            # Fallback for uncompressed data
            return json.loads(data.decode())
    
    def _encrypt_state(self, data: bytes) -> bytes:
        """Encrypt state for enterprise security"""
        if not self.encryption_key:
            return data
        # Simple XOR encryption (replace with proper encryption for production)
        key_bytes = self.encryption_key.encode()
        return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
    
    def _decrypt_state(self, data: bytes) -> bytes:
        """Decrypt state for enterprise security"""
        if not self.encryption_key:
            return data
        # XOR is symmetric
        return self._encrypt_state(data)
    
    def save_state(self, state: Dict[str, Any], message: str = "Auto-save") -> bool:
        """
        Save current developer state to disk with versioning.
        
        Args:
            state: Developer cognitive state dictionary
            message: Commit message for version history
            
        Returns:
            True if saved successfully
        """
        with self.lock:
            try:
                self._ensure_dirs()
                
                # Add metadata
                state["saved_at"] = datetime.now().isoformat()
                state["project_path"] = str(self.project_path)
                state["version_message"] = message
                
                # Compute state hash
                state_hash = self._compute_state_hash(state)
                state["state_hash"] = state_hash
                
                # Compress and encrypt
                compressed = self._compress_state(state)
                encrypted = self._encrypt_state(compressed)
                
                # Save to main state file (uncompressed for immediate access)
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                # Save compressed version for archival
                archive_file = self.history_dir / f"state_{state_hash}.json.gz"
                with open(archive_file, 'wb') as f:
                    f.write(encrypted)
                
                # Update version history
                self._add_version(state_hash, message)
                
                return True
                
            except Exception as e:
                print(f"[HCR] Error saving state: {e}")
                return False
    
    def _add_version(self, state_hash: str, message: str):
        """Add version to git-like version history"""
        versions = self._load_versions()
        
        # Get parent hash (previous version)
        parent_hashes = [versions[-1].hash] if versions else []
        
        version = StateVersion(
            hash=state_hash,
            timestamp=datetime.now().isoformat(),
            message=message,
            parent_hashes=parent_hashes,
            state_size_bytes=0
        )
        
        versions.append(version)
        
        # Keep only last 100 versions to manage storage
        versions = versions[-100:]
        
        # Save versions
        versions_data = [asdict(v) for v in versions]
        with open(self.versions_file, 'w') as f:
            json.dump(versions_data, f, indent=2)
    
    def _load_versions(self) -> List[StateVersion]:
        """Load version history"""
        if not self.versions_file.exists():
            return []
        
        try:
            with open(self.versions_file, 'r') as f:
                data = json.load(f)
                return [StateVersion(**v) for v in data]
        except:
            return []
    
    def get_version_history(self, limit: int = 50) -> List[StateVersion]:
        """Get version history like git log"""
        versions = self._load_versions()
        return versions[-limit:]
    
    def restore_version(self, state_hash: str) -> Optional[Dict[str, Any]]:
        """Restore state to specific version"""
        archive_file = self.history_dir / f"state_{state_hash}.json.gz"
        
        if not archive_file.exists():
            print(f"[HCR] Version {state_hash} not found")
            return None
        
        try:
            with open(archive_file, 'rb') as f:
                encrypted = f.read()
            
            compressed = self._decrypt_state(encrypted)
            return self._decompress_state(compressed)
        except Exception as e:
            print(f"[HCR] Error restoring version: {e}")
            return None
    
    def save_causal_graph(self, graph: CausalGraphState, graph_name: str = "main") -> bool:
        """
        Save causal graph for dependency tracking.
        
        Args:
            graph: Causal graph state
            graph_name: Name of the graph (for multiple graphs per project)
        
        Returns:
            True if saved successfully
        """
        try:
            graph_file = self.causal_dir / f"{graph_name}_graph.json"
            
            with open(graph_file, 'w') as f:
                json.dump(asdict(graph), f, indent=2)
            
            return True
        except Exception as e:
            print(f"[HCR] Error saving causal graph: {e}")
            return False
    
    def load_causal_graph(self, graph_name: str = "main") -> Optional[CausalGraphState]:
        """Load causal graph for dependency tracking"""
        graph_file = self.causal_dir / f"{graph_name}_graph.json"
        
        if not graph_file.exists():
            return None
        
        try:
            with open(graph_file, 'r') as f:
                data = json.load(f)
                return CausalGraphState(**data)
        except Exception as e:
            print(f"[HCR] Error loading causal graph: {e}")
            return None
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load developer state from disk.
        
        Returns:
            State dictionary or None if no state exists
        """
        try:
            if not self.state_file.exists():
                return None
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            return state
            
        except Exception as e:
            print(f"[HCR] Error loading state: {e}")
            return None
    
    def state_exists(self) -> bool:
        """Check if a saved state exists"""
        return self.state_file.exists()
    
    def get_last_activity_time(self) -> Optional[datetime]:
        """Get timestamp of last activity from saved state"""
        state = self.load_state()
        if state and "saved_at" in state:
            return datetime.fromisoformat(state["saved_at"])
        return None
    
    def get_gap_duration(self) -> Optional[float]:
        """
        Get minutes since last activity.
        
        Returns:
            Minutes as float, or None if no previous state
        """
        last_activity = self.get_last_activity_time()
        if not last_activity:
            return None
        
        gap = datetime.now() - last_activity
        return gap.total_seconds() / 60


@dataclass
class ProjectStateMetadata:
    """Metadata for cross-project state management"""
    project_path: str
    project_name: str
    last_accessed: str
    state_hash: str
    shared_state_keys: List[str]  # Keys that should sync across projects


class CrossProjectStateManager:
    """
    Manages cognitive state across multiple projects.
    
    Features:
    - Global state registry
    - Cross-project state sharing
    - Project switching with state migration
    - Shared operators and learned patterns
    """
    
    def __init__(self, hcr_global_dir: Optional[Path] = None):
        # Use global HCR directory in home folder
        if hcr_global_dir is None:
            home = Path.home()
            self.global_dir = home / ".hcr_global"
        else:
            self.global_dir = Path(hcr_global_dir)
        
        self.registry_file = self.global_dir / "project_registry.json"
        self.shared_state_dir = self.global_dir / "shared_states"
        self.learned_operators_dir = self.global_dir / "learned_operators"
        
        self._ensure_global_dirs()
        self._project_registry: Dict[str, ProjectStateMetadata] = {}
        self._load_registry()
    
    def _ensure_global_dirs(self):
        """Ensure global HCR directories exist"""
        self.global_dir.mkdir(exist_ok=True)
        self.shared_state_dir.mkdir(exist_ok=True)
        self.learned_operators_dir.mkdir(exist_ok=True)
    
    def _load_registry(self):
        """Load project registry from disk"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    for project_id, metadata_dict in data.items():
                        self._project_registry[project_id] = ProjectStateMetadata(**metadata_dict)
            except:
                pass
    
    def _save_registry(self):
        """Save project registry to disk"""
        data = {
            project_id: asdict(metadata) 
            for project_id, metadata in self._project_registry.items()
        }
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_project(self, project_path: str, project_name: str, 
                        shared_keys: Optional[List[str]] = None) -> str:
        """
        Register a new project for cross-project state management.
        
        Args:
            project_path: Absolute path to project
            project_name: Human-readable name
            shared_keys: State keys to share across projects
            
        Returns:
            Project ID for reference
        """
        project_id = hashlib.sha256(project_path.encode()).hexdigest()[:16]
        
        metadata = ProjectStateMetadata(
            project_path=project_path,
            project_name=project_name,
            last_accessed=datetime.now().isoformat(),
            state_hash="",
            shared_state_keys=shared_keys or []
        )
        
        self._project_registry[project_id] = metadata
        self._save_registry()
        
        return project_id
    
    def update_project_state(self, project_id: str, state_hash: str):
        """Update project state hash and access time"""
        if project_id in self._project_registry:
            self._project_registry[project_id].state_hash = state_hash
            self._project_registry[project_id].last_accessed = datetime.now().isoformat()
            self._save_registry()
    
    def get_all_projects(self) -> List[ProjectStateMetadata]:
        """Get list of all registered projects"""
        return list(self._project_registry.values())
    
    def share_state_across_projects(self, key: str, value: Any, 
                                     source_project_id: str) -> bool:
        """
        Share state value across all projects.
        
        Args:
            key: State key to share
            value: Value to share
            source_project_id: Project that created this state
            
        Returns:
            True if shared successfully
        """
        try:
            shared_state = {
                "key": key,
                "value": value,
                "source_project": source_project_id,
                "shared_at": datetime.now().isoformat(),
                "version": 1
            }
            
            shared_file = self.shared_state_dir / f"{key}.json"
            with open(shared_file, 'w') as f:
                json.dump(shared_state, f, indent=2)
            
            return True
        except Exception as e:
            print(f"[HCR] Error sharing state: {e}")
            return False
    
    def get_shared_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Get shared state value"""
        shared_file = self.shared_state_dir / f"{key}.json"
        
        if not shared_file.exists():
            return None
        
        try:
            with open(shared_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def get_shared_state_value(self, key: str) -> Optional[Any]:
        """Get just the value from shared state"""
        shared = self.get_shared_state(key)
        if shared:
            return shared.get("value")
        return None
    
    def list_shared_keys(self) -> List[str]:
        """List all shared state keys"""
        return [f.stem for f in self.shared_state_dir.glob("*.json")]
    
    def migrate_state_between_projects(self, source_project_id: str, 
                                      target_project_id: str,
                                      state_keys: List[str]) -> bool:
        """
        Migrate specific state from one project to another.
        
        Args:
            source_project_id: Source project
            target_project_id: Target project
            state_keys: Keys to migrate
            
        Returns:
            True if migrated successfully
        """
        try:
            source_path = self._project_registry[source_project_id].project_path
            target_path = self._project_registry[target_project_id].project_path
            
            source_persistence = DevStatePersistence(source_path)
            target_persistence = DevStatePersistence(target_path)
            
            source_state = source_persistence.load_state() or {}
            
            # Extract keys to migrate
            migrated_state = {k: v for k, v in source_state.items() if k in state_keys}
            
            if migrated_state:
                # Load target state and merge
                target_state = target_persistence.load_state() or {}
                target_state.update(migrated_state)
                
                # Save merged state
                target_persistence.save_state(
                    target_state, 
                    message=f"Migrated {len(state_keys)} keys from {source_project_id}"
                )
            
            return True
        except Exception as e:
            print(f"[HCR] Error migrating state: {e}")
            return False
    
    def save_learned_operator(self, operator_name: str, operator_data: Dict[str, Any],
                             source_project_id: str) -> bool:
        """
        Save learned operator for reuse across projects.
        
        Args:
            operator_name: Name of the operator
            operator_data: Operator configuration/state
            source_project_id: Project that learned this operator
            
        Returns:
            True if saved successfully
        """
        try:
            operator_file = self.learned_operators_dir / f"{operator_name}.json"
            
            operator_record = {
                "name": operator_name,
                "data": operator_data,
                "source_project": source_project_id,
                "learned_at": datetime.now().isoformat(),
                "use_count": 0
            }
            
            with open(operator_file, 'w') as f:
                json.dump(operator_record, f, indent=2)
            
            return True
        except Exception as e:
            print(f"[HCR] Error saving operator: {e}")
            return False
    
    def load_learned_operator(self, operator_name: str) -> Optional[Dict[str, Any]]:
        """Load learned operator"""
        operator_file = self.learned_operators_dir / f"{operator_name}.json"
        
        if not operator_file.exists():
            return None
        
        try:
            with open(operator_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def list_learned_operators(self) -> List[str]:
        """List all learned operators"""
        return [f.stem for f in self.learned_operators_dir.glob("*.json")]
    
    def get_recent_projects(self, days: int = 7) -> List[ProjectStateMetadata]:
        """Get projects accessed in last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for metadata in self._project_registry.values():
            try:
                accessed = datetime.fromisoformat(metadata.last_accessed)
                if accessed > cutoff:
                    recent.append(metadata)
            except:
                pass
        
        # Sort by last accessed
        recent.sort(key=lambda x: x.last_accessed, reverse=True)
        return recent


def get_project_root() -> Path:
    """
    Find project root by looking for .git directory or package.json.
    Starts from current directory and walks up.
    """
    current = Path.cwd()
    
    while current != current.parent:
        if (current / ".git").exists() or (current / "package.json").exists():
            return current
        current = current.parent
    
    return Path.cwd()  # Fallback to current directory
