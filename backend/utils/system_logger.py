"""System logging utility."""
import csv
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from config import LOG_DIR, LOG_FILE


class SystemLogger:
    """Log system events to CSV."""
    
    def __init__(self, log_file: Path = None):
        self.log_file = log_file or LOG_FILE
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()
    
    def _ensure_header(self):
        """Ensure CSV file has header."""
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "event_type", "user_email", "user_type",
                    "candidate_id", "session_id", "request_id", "message_type",
                    "content", "context_snapshot", "agent_involved",
                    "data_sources_accessed", "response_time_ms", "status",
                    "error_message", "metadata"
                ])
    
    def _write_row(self, row: Dict[str, Any]):
        """Write a row to the log file."""
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    row.get("timestamp", ""),
                    row.get("event_type", ""),
                    row.get("user_email", ""),
                    row.get("user_type", ""),
                    row.get("candidate_id", ""),
                    row.get("session_id", ""),
                    row.get("request_id", ""),
                    row.get("message_type", ""),
                    str(row.get("content", "")),
                    str(row.get("context_snapshot", "")),
                    row.get("agent_involved", ""),
                    row.get("data_sources_accessed", ""),
                    row.get("response_time_ms", ""),
                    row.get("status", ""),
                    row.get("error_message", ""),
                    str(row.get("metadata", ""))
                ])
        except Exception as e:
            print(f"Error writing to log: {e}")
    
    def log(
        self,
        event_type: str,
        user_email: Optional[str] = None,
        user_type: Optional[str] = None,
        candidate_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        status: str = "Success",
        error_message: Optional[str] = None,
        **kwargs
    ):
        """Log a general event."""
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_email": user_email or "",
            "user_type": user_type or "",
            "candidate_id": candidate_id or "",
            "session_id": session_id or "",
            "request_id": request_id or "",
            "message_type": "",
            "content": "",
            "context_snapshot": "",
            "agent_involved": "",
            "data_sources_accessed": "",
            "response_time_ms": "",
            "status": status,
            "error_message": error_message or "",
            "metadata": kwargs
        }
        self._write_row(row)
    
    def log_message(
        self,
        user_email: str,
        user_type: str,
        message: str,
        candidate_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log a user message."""
        self.log(
            event_type="Message",
            user_email=user_email,
            user_type=user_type,
            candidate_id=candidate_id,
            session_id=session_id,
            request_id=request_id,
            message_type="User Request",
            content=message
        )
    
    def log_response(
        self,
        user_email: str,
        user_type: str,
        response: str,
        candidate_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ):
        """Log a system response."""
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "Response",
            "user_email": user_email,
            "user_type": user_type,
            "candidate_id": candidate_id or "",
            "session_id": session_id or "",
            "request_id": request_id or "",
            "message_type": "System Response",
            "content": response,
            "context_snapshot": str(context_snapshot) if context_snapshot else "",
            "agent_involved": "",
            "data_sources_accessed": "",
            "response_time_ms": response_time_ms or "",
            "status": "Success",
            "error_message": "",
            "metadata": ""
        }
        self._write_row(row)
    
    def log_context_update(
        self,
        user_email: str,
        user_type: str,
        candidate_id: str,
        field: str,
        old_value: Any,
        new_value: Any
    ):
        """Log a context update."""
        self.log(
            event_type="ContextUpdate",
            user_email=user_email,
            user_type=user_type,
            candidate_id=candidate_id,
            metadata={"field": field, "old_value": str(old_value), "new_value": str(new_value)}
        )
    
    def log_feedback(
        self,
        user_email: str,
        user_type: str,
        response_id: str,
        feedback_type: str,
        comment: Optional[str] = None,
        candidate_id: Optional[str] = None
    ):
        """Log user feedback."""
        self.log(
            event_type="Feedback",
            user_email=user_email,
            user_type=user_type,
            candidate_id=candidate_id,
            metadata={
                "response_id": response_id,
                "feedback_type": feedback_type,
                "comment": comment or ""
            }
        )


# Singleton instance
system_logger = SystemLogger()

