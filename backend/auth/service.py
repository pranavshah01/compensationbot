"""Authentication and authorization."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from models import UserType

# Hardcoded users from PRD
USERS = {
    "riot-comp-user1@example.com": {
        "password": "Welcome@121",
        "user_type": UserType.COMP_TEAM,
        "first_name": "User1"
    },
    "riot-comp-user2@example.com": {
        "password": "Welcome@122",
        "user_type": UserType.COMP_TEAM,
        "first_name": "User2"
    },
    "riot-comp-user3@example.com": {
        "password": "Welcome@123",
        "user_type": UserType.COMP_TEAM,
        "first_name": "User3"
    },
    "riot-rec-user1@example.com": {
        "password": "Welcome@121",
        "user_type": UserType.RECRUITMENT_TEAM,
        "first_name": "User1"
    },
    "riot-rec-user2@example.com": {
        "password": "Welcome@122",
        "user_type": UserType.RECRUITMENT_TEAM,
        "first_name": "User2"
    },
    "riot-rec-user3@example.com": {
        "password": "Welcome@123",
        "user_type": UserType.RECRUITMENT_TEAM,
        "first_name": "User3"
    },
}

SECRET_KEY = "comp-agent-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user with email and password."""
    user = USERS.get(email)
    if not user:
        return None
    if user["password"] != password:  # Simple comparison for MVP
        return None
    return {
        "email": email,
        "user_type": user["user_type"],
        "first_name": user["first_name"]
    }


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[dict]:
    """Get user information from token."""
    payload = verify_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    if email and email in USERS:
        user = USERS[email]
        return {
            "email": email,
            "user_type": user["user_type"],
            "first_name": user["first_name"]
        }
    return None



