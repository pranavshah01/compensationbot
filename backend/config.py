"""Configuration management for the backend."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str
    gemini_api_key: str
    
    # Backend Configuration
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # LLM Configuration
    openai_model: str = "gpt-4o"  # Default to GPT-4o, can override via env var
    
    # Agent Configuration
    enable_judge_agent: bool = True  # Enable/disable Judge agent (default: True)
    
    # Testing Configuration
    use_real_llm_in_tests: bool = False  # Set to True to use real LLM in tests (requires API keys)
    
    # Data Paths
    data_dir: str = "data"  # Relative to backend directory
    comp_ranges_file: str = "CompRanges.csv"
    employee_roster_file: str = "EmployeeRoster.csv"
    log_dir: str = "data/logs"
    
    # Context Persistence
    context_retention_days: int = 60
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Initialize settings
settings = Settings()

# Resolve absolute paths
BASE_DIR = Path(__file__).parent.resolve()
# Use backend/data directory (not ../data)
DATA_DIR = (BASE_DIR / "data").resolve()
LOG_DIR = (BASE_DIR / settings.log_dir).resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# File paths
COMP_RANGES_PATH = DATA_DIR / settings.comp_ranges_file
EMPLOYEE_ROSTER_PATH = DATA_DIR / settings.employee_roster_file
LOG_FILE = LOG_DIR / "system_logs.csv"

