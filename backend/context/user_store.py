"""User context storage for tracking current candidate."""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from models import UserContext
from config import DATA_DIR


class UserContextStore:
    """Store user's current candidate context."""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or DATA_DIR
        self.user_contexts_file = self.data_dir / "user_contexts.json"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure user contexts file exists."""
        if not self.user_contexts_file.exists():
            with open(self.user_contexts_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_user_contexts(self) -> dict:
        """Load all user contexts."""
        try:
            with open(self.user_contexts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_user_contexts(self, user_contexts: dict):
        """Save all user contexts."""
        try:
            with open(self.user_contexts_file, 'w', encoding='utf-8') as f:
                json.dump(user_contexts, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving user contexts: {e}")
    
    def get_current_candidate(self, user_email: str) -> Optional[str]:
        """Get user's current candidate ID."""
        user_contexts = self._load_user_contexts()
        user_ctx = user_contexts.get(user_email)
        if user_ctx:
            return user_ctx.get("current_candidate_id")
        return None
    
    def set_current_candidate(self, user_email: str, candidate_id: Optional[str]):
        """Set user's current candidate ID."""
        user_contexts = self._load_user_contexts()
        
        if user_email not in user_contexts:
            user_contexts[user_email] = {
                "user_email": user_email,
                "current_candidate_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        
        user_contexts[user_email]["current_candidate_id"] = candidate_id
        user_contexts[user_email]["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        self._save_user_contexts(user_contexts)
    
    def clear_current_candidate(self, user_email: str):
        """Clear user's current candidate."""
        self.set_current_candidate(user_email, None)


# Singleton instance
user_context_store = UserContextStore()

