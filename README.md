# Compensation Recommendation Assistant

An AI-powered conversational assistant that helps Compensation and Recruitment teams generate data-driven compensation recommendations for job candidates.

## Features

- **Conversational Interface**: Natural language interaction to collect candidate information
- **Market Data Analysis**: Queries compensation ranges from internal data (CompRanges.csv)
- **Internal Parity Checks**: Compares against existing employee salaries (EmployeeRoster.csv)
- **Counter Offer Handling**: Dynamically adjusts recommendations based on competing offers
- **Interview Feedback Integration**: Factors in Must Hire/Strong Hire/Hire assessments
- **Recommendation History**: Tracks all recommendations per candidate
- **Role-Based Access**: Compensation Team (full access) vs Recruitment Team (view only)

## Prerequisites

- **Python 3.10** (required)
- **Node.js 18+** (for frontend)
- **npm** or **yarn**

## Project Structure

```
compassistant/
├── backend/                 # FastAPI Python backend
│   ├── agents/             # LangGraph agent workflow
│   ├── auth/               # Authentication service
│   ├── context/            # Candidate context management
│   ├── data/               # CSV data files and JSON stores
│   ├── messages/           # Message history storage
│   ├── main.py             # FastAPI application
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js React frontend
│   ├── app/                # Next.js app router
│   ├── components/         # React components
│   └── lib/                # API client and state management
├── docs/                   # Documentation and deliverables
└── start.sh               # Start both servers
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd compassistant
```

### 2. Backend Setup

```bash
cd backend

# Create Python virtual environment (Python 3.10 required)
python3.10 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

**Important**: Create a `.env` file from the example template:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add your API keys:

```dotenv
# API Keys for LLM Providers (at least one required)
GEMINI_API_KEY="your-gemini-api-key"
OPENAI_API_KEY="your-openai-api-key"

# Backend Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

**Getting API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Google Gemini**: https://makersuite.google.com/app/apikey

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

## Running the Application

### Option 1: Start Both Servers (Recommended)

From the project root:

```bash
./start.sh
```

This starts both backend (port 8000) and frontend (port 3000).

### Option 2: Start Servers Individually

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Option 3: Use Individual Scripts

```bash
./start-backend.sh  # Start backend only
./start-frontend.sh # Start frontend only
```

## Accessing the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Test Users

The application includes pre-configured test users:

| Email | Password | Role |
|-------|----------|------|
| `riot-comp-user1@example.com` | `password123` | Compensation Team |

## Testing the Application

### Basic Conversation Flow

1. Login with a test user
2. Start a new conversation:
   ```
   I need a compensation recommendation for CAND-001
   ```
3. Provide required information when prompted:
   - Job Title (e.g., "Senior Software Engineer")
   - Job Level (P1-P5)
   - Location (LAX, SEA, STL, DUB, SHA, SYD, SIN)
   - Job Family (Engineering, Finance, Legal, HR, Sales, Marketing, Operations, Executive)
   - Interview Feedback (Must Hire, Strong Hire, Hire)

4. Receive a compensation recommendation with:
   - Base salary
   - Bonus percentage
   - Equity grant
   - Total compensation

### Testing Counter Offers

```
The candidate has a counter offer of $350,000 from Google
```

The system will adjust the recommendation to be competitive.

## Stopping the Application

```bash
./stop.sh
```
Or press `Ctrl+C` in each terminal.

## Troubleshooting

### Common Issues

1. **"Python 3.10 not found"**
   - Install Python 3.10 from https://www.python.org/downloads/
   - Use `python3.10` explicitly when creating the venv

2. **"Module not found" errors**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt` again

3. **"API key not configured"**
   - Verify `.env` file exists in `backend/`
   - Check that API keys are correctly set

4. **"Port already in use"**
   - Run `./stop.sh` to kill existing processes
   - Or manually: `lsof -ti:8000 | xargs kill -9`

5. **Frontend not connecting to backend**
   - Ensure backend is running on port 8000
   - Check browser console for CORS errors

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/stream` | Send message and stream response |
| GET | `/api/context/{candidate_id}` | Get candidate context |
| POST | `/api/auth/login` | User authentication |
| GET | `/api/user/candidates` | List user's candidates |
| GET | `/api/messages` | Get message history |

## Architecture

The application uses a LangGraph-based agent workflow:

```
User Message → Coordinator → Research Agent → Judge Agent → Response
                   ↓              ↓
              Context Store   DataCollector
                              (CompRanges.csv,
                               EmployeeRoster.csv)
```

See `docs/deliverables/B_High_Level_Architecture.md` for detailed architecture documentation.

## License

Proprietary - Internal Use Only
