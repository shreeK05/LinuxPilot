"""
Audit Chain
Tamper-evident audit log with hash chain verification
Implements the "Durability" property of ACID
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from linuxpilot.models import AuditEntry
from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class AuditChain:
    """
    Tamper-evident audit log with hash chain
    Each entry is chained to the previous one via SHA-256
    """
    
    def __init__(self, task_id: str, audit_dir: Path = None):
        self.task_id = task_id
        self.audit_dir = audit_dir or settings.AUDIT_DIR
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.audit_file = self.audit_dir / f"{task_id}.audit"
        self.seq = 0
        self.prev_hash = "0" * 64  # Genesis hash
    
    def _compute_hash(self, entry_data: dict, prev_hash: str) -> str:
        """
        Compute hash for an audit entry
        
        hash = SHA256(prev_hash || canonical_json(entry_without_hash))
        """
        # Remove hash field if present
        entry_without_hash = {k: v for k, v in entry_data.items() if k != "hash"}
        
        # Canonical JSON (sorted keys, no whitespace)
        canonical = json.dumps(entry_without_hash, sort_keys=True, separators=(",", ":"))
        
        # Hash previous hash + canonical entry
        hash_input = prev_hash + canonical
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def append(
        self,
        kind: str,
        payload: Dict[str, Any],
        step: Optional[str] = None,
    ) -> AuditEntry:
        """
        Append an entry to the audit chain
        
        Args:
            kind: Kind of event (action, verify, rollback, violation, approval, commit)
            payload: Event payload
            step: Optional step ID
        
        Returns:
            The created audit entry
        """
        entry_data = {
            "seq": self.seq,
            "ts": datetime.utcnow().isoformat() + "Z",
            "task": self.task_id,
            "step": step,
            "kind": kind,
            "payload": payload,
            "prev": self.prev_hash,
        }
        
        # Compute hash
        entry_hash = self._compute_hash(entry_data, self.prev_hash)
        entry_data["hash"] = entry_hash
        
        # Create entry object
        entry = AuditEntry(**entry_data)
        
        # Append to file
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry.model_dump()) + "\n")
            f.flush()
        
        # Update state
        self.seq += 1
        self.prev_hash = entry_hash
        
        logger.debug(f"Appended audit entry {entry.seq}: {kind}")
        return entry
    
    def verify(self) -> tuple[bool, Optional[str]]:
        """
        Verify the integrity of the audit chain
        
        Returns:
            (is_valid, error_message)
        """
        if not self.audit_file.exists():
            return True, None  # Empty chain is valid
        
        try:
            entries = []
            with open(self.audit_file, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            
            if not entries:
                return True, None
            
            # Verify chain
            prev_hash = "0" * 64  # Genesis hash
            
            for i, entry_data in enumerate(entries):
                # Recompute hash
                entry_without_hash = {k: v for k, v in entry_data.items() if k != "hash"}
                canonical = json.dumps(entry_without_hash, sort_keys=True, separators=(",", ":"))
                computed_hash = hashlib.sha256((prev_hash + canonical).encode()).hexdigest()
                
                # Check hash
                if computed_hash != entry_data["hash"]:
                    return False, f"Hash mismatch at entry {i}: expected {computed_hash}, got {entry_data['hash']}"
                
                # Check prev hash link
                if entry_data["prev"] != prev_hash:
                    return False, f"Chain broken at entry {i}: prev={entry_data['prev']}, expected={prev_hash}"
                
                prev_hash = entry_data["hash"]
            
            logger.info(f"Audit chain verified: {len(entries)} entries")
            return True, None
            
        except Exception as e:
            logger.error(f"Audit verification failed: {e}")
            return False, str(e)
    
    def get_entries(self, kind_filter: Optional[str] = None) -> List[AuditEntry]:
        """
        Get all entries from the audit log
        
        Args:
            kind_filter: Optional filter by event kind
        
        Returns:
            List of audit entries
        """
        if not self.audit_file.exists():
            return []
        
        entries = []
        with open(self.audit_file, "r") as f:
            for line in f:
                if line.strip():
                    entry = AuditEntry.model_validate_json(line)
                    if kind_filter is None or entry.kind == kind_filter:
                        entries.append(entry)
        
        return entries
    
    def get_final_hash(self) -> Optional[str]:
        """
        Get the final hash of the audit chain
        Can be used for external anchoring
        """
        if not self.audit_file.exists():
            return None
        
        with open(self.audit_file, "r") as f:
            lines = f.readlines()
        
        if not lines:
            return None
        
        last_entry = json.loads(lines[-1])
        return last_entry["hash"]
    
    def clear(self):
        """Clear the audit log (for testing)"""
        if self.audit_file.exists():
            self.audit_file.unlink()
        self.seq = 0
        self.prev_hash = "0" * 64
