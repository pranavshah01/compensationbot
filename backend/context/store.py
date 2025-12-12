"""Candidate context storage."""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from models import CandidateContext, CandidateState
from config import DATA_DIR


class ContextStore:
    """Store and retrieve candidate contexts."""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or DATA_DIR
        self.contexts_file = self.data_dir / "contexts.json"
        self.audit_log_file = self.data_dir / "context_audit_log.json"
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure context files exist."""
        if not self.contexts_file.exists():
            with open(self.contexts_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        if not self.audit_log_file.exists():
            with open(self.audit_log_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_contexts(self) -> Dict[str, Any]:
        """Load all contexts from file."""
        try:
            with open(self.contexts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_contexts(self, contexts: Dict[str, Any]):
        """Save all contexts to file."""
        try:
            with open(self.contexts_file, 'w', encoding='utf-8') as f:
                json.dump(contexts, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving contexts: {e}")
    
    def _load_audit_log(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load audit log."""
        try:
            with open(self.audit_log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure it's a dict (not a list)
                if isinstance(data, list):
                    return {}
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    
    def _save_audit_log(self, audit_log: Dict[str, List[Dict[str, Any]]]):
        """Save audit log."""
        try:
            with open(self.audit_log_file, 'w', encoding='utf-8') as f:
                json.dump(audit_log, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving audit log: {e}")
    
    def get_context(self, candidate_id: str) -> Optional[CandidateContext]:
        """Get context for a candidate."""
        contexts = self._load_contexts()
        if candidate_id not in contexts:
            return None
        
        try:
            ctx_data = contexts[candidate_id]
            # Ensure candidate_id is set
            ctx_data["candidate_id"] = candidate_id
            return CandidateContext(**ctx_data)
        except Exception as e:
            print(f"Error loading context for {candidate_id}: {e}")
            return None
    
    def save_context(
        self,
        candidate_id: str,
        context_data: Dict[str, Any],
        updated_by: Optional[str] = None,
        replace_existing: bool = False
    ) -> None:
        """Save or update candidate context.
        
        Args:
            candidate_id: The candidate ID
            context_data: New context data to save
            updated_by: User making the update
            replace_existing: If True and candidate exists, replace core fields but merge additional info
        """
        if not candidate_id:
            return
        
        contexts = self._load_contexts()
        
        # Get existing context or create new
        existing = contexts.get(candidate_id, {})
        is_new_candidate = len(existing) == 0
        
        # Define core fields that should be replaced (not merged)
        core_fields = {"job_title", "job_level", "location", "job_family", "interview_feedback"}
        
        # Define additional fields that should always be merged (not replaced)
        additional_fields = {"proficiency", "additional_data", "counter_offer", "competing_offer", 
                            "equity_request", "joining_bonus", "candidate_feedback", "notes"}
        
        # Determine if we should replace core fields or merge everything
        if replace_existing and not is_new_candidate:
            # Replace core fields but merge additional fields
            original_created_at = existing.get("created_at")
            original_created_by = existing.get("created_by")
            
            # Start with existing context
            updated = {**existing}
            
            # Replace core fields from context_data
            for field in core_fields:
                if field in context_data:
                    updated[field] = context_data[field]
            
            # Merge additional fields (deep merge for additional_data dict)
            for field in additional_fields:
                if field in context_data:
                    if field == "additional_data" and isinstance(updated.get(field), dict) and isinstance(context_data[field], dict):
                        # Deep merge for additional_data
                        updated[field] = {**updated.get(field, {}), **context_data[field]}
                    else:
                        # For other additional fields, merge (prefer new value if provided)
                        updated[field] = context_data[field]
            
            # Also merge any other fields not in core or additional (like recommendation_history)
            for key, value in context_data.items():
                if key not in core_fields and key not in additional_fields and key not in ["candidate_id", "created_at", "created_by", "updated_at", "updated_by", "state"]:
                    if key == "recommendation_history" and isinstance(updated.get(key), list) and isinstance(value, list):
                        # For recommendation_history, append new items
                        updated[key] = updated.get(key, []) + value
                    else:
                        updated[key] = value
            
            updated["candidate_id"] = candidate_id
            updated["updated_at"] = datetime.now(timezone.utc).isoformat()
            if updated_by:
                updated["updated_by"] = updated_by
            
            # Preserve original creation metadata
            if original_created_at:
                updated["created_at"] = original_created_at
            else:
                updated["created_at"] = datetime.now(timezone.utc).isoformat()
            
            if original_created_by:
                updated["created_by"] = original_created_by
            
            # Ensure state exists
            if "state" not in updated:
                updated["state"] = CandidateState.ACTIVE.value
            
            # Log replacement if different user
            if original_created_by and updated_by and original_created_by != updated_by:
                self._log_context_replacement(
                    candidate_id,
                    existing,
                    updated,
                    original_created_by,
                    updated_by
                )
            else:
                # Still log as field changes, but exclude created_by from tracking
                self._log_context_changes(candidate_id, existing, updated, updated_by, is_replacement=True)
        else:
            # Merge new data (default behavior) - but still handle additional_data specially
            updated = {**existing}
            
            # Merge all fields, with special handling for additional_data
            for key, value in context_data.items():
                if key == "additional_data" and isinstance(updated.get(key), dict) and isinstance(value, dict):
                    # Deep merge for additional_data
                    updated[key] = {**updated.get(key, {}), **value}
                elif key == "recommendation_history" and isinstance(updated.get(key), list) and isinstance(value, list):
                    # Append new recommendation history items
                    updated[key] = updated.get(key, []) + value
                else:
                    # Regular merge (new values override existing)
                    updated[key] = value
            
            updated["candidate_id"] = candidate_id
            updated["updated_at"] = datetime.now(timezone.utc).isoformat()
            if updated_by:
                updated["updated_by"] = updated_by
            
            # For new candidates, set created_by
            if is_new_candidate:
                updated["created_by"] = updated_by or "system"
            
            # Ensure created_at exists
            if "created_at" not in updated:
                updated["created_at"] = datetime.now(timezone.utc).isoformat()
            
            # Ensure state exists
            if "state" not in updated:
                updated["state"] = CandidateState.ACTIVE.value
            
            # Log changes to audit log
            self._log_context_changes(candidate_id, existing, updated, updated_by, is_replacement=False)
        
        # Save
        contexts[candidate_id] = updated
        self._save_contexts(contexts)
    
    def _log_context_changes(
        self,
        candidate_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        updated_by: Optional[str],
        is_replacement: bool = False
    ):
        """Log context changes to audit log."""
        audit_log = self._load_audit_log()
        
        if candidate_id not in audit_log:
            audit_log[candidate_id] = []
        
        # Track field changes
        excluded_fields = ["updated_at", "created_at", "candidate_id"]
        # During replacement, exclude created_by from field change tracking
        # (it's handled separately by _log_context_replacement)
        if is_replacement:
            excluded_fields.append("created_by")
        
        for key, new_value in new_data.items():
            if key in excluded_fields:
                continue
            old_value = old_data.get(key)
            if old_value != new_value:
                audit_log[candidate_id].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user": updated_by or "system",
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        self._save_audit_log(audit_log)
    
    def _log_context_replacement(
        self,
        candidate_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        original_creator: str,
        replacing_user: str
    ):
        """Log when an entire context is replaced by a different user."""
        audit_log = self._load_audit_log()
        
        if candidate_id not in audit_log:
            audit_log[candidate_id] = []
        
        # Log the replacement event
        audit_log[candidate_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": replacing_user,
            "field": "context_replacement",
            "old_value": f"Context created by {original_creator}",
            "new_value": f"Context replaced by {replacing_user}",
            "original_creator": original_creator,
            "replacing_user": replacing_user,
            "replacement_type": "full_context_replacement"
        })
        
        self._save_audit_log(audit_log)
    
    def reset_context(self, candidate_id: str, updated_by: str) -> bool:
        """Reset context for a candidate."""
        contexts = self._load_contexts()
        if candidate_id not in contexts:
            return False
        
        # Delete context
        del contexts[candidate_id]
        self._save_contexts(contexts)
        
        # Log reset
        audit_log = self._load_audit_log()
        if candidate_id not in audit_log:
            audit_log[candidate_id] = []
        audit_log[candidate_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": updated_by,
            "field": "reset",
            "old_value": "exists",
            "new_value": "deleted"
        })
        self._save_audit_log(audit_log)
        
        return True
    
    def get_audit_log(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Get audit log for a candidate."""
        audit_log = self._load_audit_log()
        return audit_log.get(candidate_id, [])
    
    def get_active_candidates(self, user_email: str) -> List[CandidateContext]:
        """Get active candidates for a user."""
        contexts = self._load_contexts()
        active = []
        
        for candidate_id, ctx_data in contexts.items():
            try:
                ctx = CandidateContext(candidate_id=candidate_id, **ctx_data)
                if ctx.state == CandidateState.ACTIVE:
                    # Check if user has access (for now, all users see all candidates)
                    active.append(ctx)
            except Exception:
                continue
        
        return active
    
    def get_closed_candidates(self, user_email: str) -> List[CandidateContext]:
        """Get closed candidates for a user."""
        contexts = self._load_contexts()
        closed = []
        
        for candidate_id, ctx_data in contexts.items():
            try:
                ctx = CandidateContext(candidate_id=candidate_id, **ctx_data)
                if ctx.state == CandidateState.CLOSED:
                    closed.append(ctx)
            except Exception:
                continue
        
        return closed


# Singleton instance
context_store = ContextStore()

