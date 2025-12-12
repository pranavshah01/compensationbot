"""Data models for the application."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UserType(str, Enum):
    COMP_TEAM = "Comp Team"
    RECRUITMENT_TEAM = "Recruitment Team"


class FeedbackType(str, Enum):
    THUMBS_DOWN = "thumbs_down"
    REPORT_ERROR = "report_error"


class CandidateState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_type: str
    user_email: str
    current_candidate_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    candidate_id: Optional[str] = None
    session_id: Optional[str] = None


class ContextResetRequest(BaseModel):
    candidate_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    response_id: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    candidate_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str


class RecommendationHistoryItem(BaseModel):
    timestamp: str
    context_snapshot: Dict[str, Any]
    recommendation: Dict[str, Any]


class CandidateContext(BaseModel):
    """Structured candidate context."""
    candidate_id: str
    state: CandidateState = CandidateState.ACTIVE
    job_title: Optional[str] = None
    job_level: Optional[str] = None  # P1-P5
    location: Optional[str] = None
    job_family: Optional[str] = None
    interview_feedback: Optional[str] = None  # Must Hire, Strong Hire, Hire
    proficiency: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    created_by: Optional[str] = None  # User who originally created this candidate
    updated_by: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    recommendation_history: List[RecommendationHistoryItem] = Field(default_factory=list)


class UserContext(BaseModel):
    """User's current session context."""
    user_email: str
    current_candidate_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MarketCompensation(BaseModel):
    """Market compensation data from CompRanges.csv."""
    currency: str
    min: float
    max: float
    range: str


class InternalParity(BaseModel):
    """Internal parity data from EmployeeRoster.csv."""
    min: float
    max: float
    count: int


class ResearchOutput(BaseModel):
    """Output from Research Agent."""
    market_data_available: bool
    market_compensation: Optional[MarketCompensation] = None
    internal_parity: Optional[InternalParity] = None


class RecommendationOutput(BaseModel):
    """Final recommendation output."""
    base_salary: float
    base_salary_percent_of_range: float
    bonus_percentage: float
    equity_amount: float
    total_compensation: float
    reasoning: Dict[str, str]
    market_data: Optional[MarketCompensation] = None
    internal_parity: Optional[InternalParity] = None


class Message(BaseModel):
    """Message model for storing conversation history."""
    timestamp: datetime
    user_email: str
    message: str
    response: str
    session_id: str
    request_id: str
    candidate_id: str


