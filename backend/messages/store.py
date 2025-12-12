"""Message storage for conversation history - stored per USER, not per candidate."""
import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from models import Message
from config import DATA_DIR


class MessageStore:
    """Store and retrieve messages per USER (not per candidate).
    
    Messages are stored by user_email. Each message can optionally have a candidate_id
    to track which candidate was being discussed, but the conversation history
    belongs to the user.
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or DATA_DIR
        self.messages_dir = self.data_dir / "messages"
        self.messages_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_message_file(self, user_email: str) -> Path:
        """Get the message file path for a user."""
        # Sanitize user_email for filename
        safe_email = user_email.replace("@", "_at_").replace(".", "_").replace("/", "_")
        return self.messages_dir / f"user_{safe_email}.json"
    
    def save_message(
        self,
        user_email: str,
        message: str,
        response: str,
        session_id: str,
        request_id: str,
        candidate_id: Optional[str] = None
    ) -> None:
        """Save a user message and assistant response.
        
        Messages are stored per user. candidate_id is optional metadata.
        """
        if not user_email:
            return  # Must have user_email
        
        message_file = self._get_message_file(user_email)
        
        # Load existing messages
        messages = []
        if message_file.exists():
            try:
                with open(message_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            except Exception:
                messages = []
        
        # Create new message entry
        new_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_email": user_email,
            "message": message,
            "response": response,
            "session_id": session_id,
            "request_id": request_id,
            "candidate_id": candidate_id  # Optional - can be None for greetings
        }
        
        # Append to messages (newest last)
        messages.append(new_message)
        
        # Save back to file
        try:
            with open(message_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving message: {e}")
    
    def get_messages(
        self,
        user_email: str,
        limit: int = 10,
        offset: int = 0,
        candidate_id: Optional[str] = None
    ) -> List[dict]:
        """Retrieve messages for a user with pagination.
        
        If candidate_id provided, filter to only that candidate's messages.
        Returns newest first.
        """
        if not user_email:
            return []
        
        message_file = self._get_message_file(user_email)
        
        if not message_file.exists():
            return []
        
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Filter by candidate_id if provided
            if candidate_id:
                messages = [m for m in messages if m.get("candidate_id") == candidate_id]
            
            # Reverse to get newest first
            messages_reversed = list(reversed(messages))
            
            # Apply pagination
            start = offset
            end = offset + limit
            paginated = messages_reversed[start:end]
            
            return paginated
        except Exception as e:
            print(f"Error loading messages: {e}")
            return []
    
    def get_all_messages(self, user_email: str, limit: int = 50) -> List[dict]:
        """Get all messages for a user (for displaying full conversation)."""
        if not user_email:
            return []
        
        message_file = self._get_message_file(user_email)
        
        if not message_file.exists():
            return []
        
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Return most recent messages (oldest first for display)
            return messages[-limit:] if len(messages) > limit else messages
        except Exception as e:
            print(f"Error loading messages: {e}")
            return []
    
    def get_message_count(self, user_email: str, candidate_id: Optional[str] = None) -> int:
        """Get total message count for a user (optionally filtered by candidate)."""
        if not user_email:
            return 0
        
        message_file = self._get_message_file(user_email)
        
        if not message_file.exists():
            return 0
        
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if candidate_id:
                messages = [m for m in messages if m.get("candidate_id") == candidate_id]
            
            return len(messages)
        except Exception:
            return 0
    
    def get_most_recent_candidate_id(self, user_email: str) -> Optional[str]:
        """Get the most recent candidate ID from user's message history."""
        if not user_email:
            return None
        
        message_file = self._get_message_file(user_email)
        
        if not message_file.exists():
            return None
        
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Search from newest to oldest for a message with candidate_id
            for msg in reversed(messages):
                if msg.get("candidate_id"):
                    return msg["candidate_id"]
            
            return None
        except Exception:
            return None


# Singleton instance
message_store = MessageStore()
