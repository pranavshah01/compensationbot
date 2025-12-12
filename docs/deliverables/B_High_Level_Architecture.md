# B. High-Level Architecture

## Architecture Overview

The Compensation Recommendation Conversational Assistant is a POC (Proof of Concept) built with a three-tier architecture: frontend (Next.js), backend (FastAPI), and agent layer (LangGraph). The system uses a **three-agent architecture** with the following components:

1. **Coordinator Agent**: Entry point that handles user messages, extracts context, and routes to research
2. **Research Agent**: Generates compensation recommendations using data from the Data Collector
3. **Data Collector Agent**: Sub-agent called by Research to fetch market and parity data from CSV files
4. **Judge Agent** (Optional): Validates recommendations against data (can be enabled via settings)

The system also features a **dynamic additional_context system** that captures any relevant information from user messages (counter offers, salary expectations, urgency, etc.) and accumulates it across the conversation.

## System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Next.js Frontend<br/>React + TypeScript]
        Chat[Chat Interface]
        ContextPanel[Context Panel]
        ExplanationPanel[Explanation Panel]
        Login[Login Page]
        SSE_Client[SSE Client]
        
        UI --> Chat
        UI --> ContextPanel
        UI --> ExplanationPanel
        UI --> Login
        UI --> SSE_Client
    end
    
    subgraph "API Layer"
        FastAPI[FastAPI Backend<br/>Python 3.10+]
        REST[REST API Endpoints]
        Auth[Authentication]
        SSE_Handler[SSE Streaming]
        ContextMgr[Context Management]
        MessageStore[Message Store<br/>Per-User Storage]
        
        FastAPI --> REST
        FastAPI --> Auth
        FastAPI --> SSE_Handler
        FastAPI --> ContextMgr
        FastAPI --> MessageStore
    end
    
    subgraph "Agent Layer"
        LangGraph[LangGraph State Machine]
        Coordinator[Coordinator Agent<br/>- Interprets messages<br/>- Extracts additional_context<br/>- Normalizes inputs<br/>- Checks required fields]
        Research[Research Agent<br/>- Calls Data Collector<br/>- Generates recommendation<br/>- Handles counter offers<br/>- Ensures zero hallucination]
        DataCollector[Data Collector Agent<br/>SUB-AGENT<br/>- Exact-match CSV lookups<br/>- Returns raw data only<br/>- Called by Research when needed]
        Judge[Judge Agent<br/>OPTIONAL<br/>- Validates recommendation<br/>- Checks data accuracy]
        
        LangGraph --> Coordinator
        Coordinator -->|If data complete| Research
        Research -->|Invoke sub-agent| DataCollector
        DataCollector -->|Raw data| Research
        Research -->|If enabled| Judge
        Research -->|Recommendation| LangGraph
        Judge -->|Validated| LangGraph
        Coordinator -->|If missing fields| LangGraph
    end
    
    subgraph "Data Layer"
        CompRanges[CompRanges.csv<br/>Market Compensation]
        EmployeeRoster[EmployeeRoster.csv<br/>Internal Parity]
        ContextStore[contexts.json<br/>Per-Candidate Context]
        UserMessages[user_*.json<br/>Per-User Messages]
        SystemLogs[system_logs.csv<br/>Event Logging]
    end
    
    SSE_Client <-->|HTTP/SSE| SSE_Handler
    Chat <-->|HTTP POST| REST
    Login <-->|HTTP POST| Auth
    ContextPanel <-->|HTTP GET| ContextMgr
    
    FastAPI <-->|LangGraph State| LangGraph
    
    DataCollector -->|Exact-match lookup| CompRanges
    DataCollector -->|Exact-match lookup| EmployeeRoster
    ContextMgr <-->|Read/Write| ContextStore
    MessageStore <-->|Read/Write| UserMessages
    FastAPI -->|Log events| SystemLogs
    
    style UI fill:#e1f5ff
    style FastAPI fill:#fff4e1
    style LangGraph fill:#e8f5e9
    style Coordinator fill:#f3e5f5
    style Research fill:#f3e5f5
    style DataCollector fill:#ffe0b2
    style Judge fill:#f3e5f5
    style CompRanges fill:#ffebee
    style EmployeeRoster fill:#ffebee
    style ContextStore fill:#ffebee
    style UserMessages fill:#ffebee
```

## Agent Workflow

```mermaid
stateDiagram-v2
    [*] --> UserMessage: User sends message
    
    UserMessage --> Coordinator: FastAPI receives request
    
    state Coordinator {
        [*] --> ParseMessage: Parse user message
        ParseMessage --> ExtractContext: Extract additional_context
        ExtractContext --> UpdateContext: Update candidate context
        UpdateContext --> NormalizeInputs: Normalize inputs
        NormalizeInputs --> CheckFields: Check required fields
        CheckFields --> RouteDecision: Route decision
    }
    
    Coordinator --> AskUser: Missing fields
    Coordinator --> Research: All fields present
    
    AskUser --> [*]: Response to user
    
    state Research {
        [*] --> CheckDataFresh: Check if data is fresh
        CheckDataFresh --> CallDataCollector: Data stale or missing
        CheckDataFresh --> UseExistingData: Data is fresh
        CallDataCollector --> DataCollector: Invoke sub-agent
        DataCollector --> ProcessData: Raw data returned
        UseExistingData --> ProcessData: Use cached data
        ProcessData --> CheckCounterOffer: Check additional_context
        CheckCounterOffer --> AdjustRecommendation: Counter offer exists
        CheckCounterOffer --> GenerateRecommendation: No counter offer
        AdjustRecommendation --> GenerateRecommendation: Adjust for counter offer
        GenerateRecommendation --> ValidateOutput: Ensure zero hallucination
        ValidateOutput --> CreateReasoning: Create reasoning breakdown
    }
    
    state DataCollector {
        [*] --> LookupMarket: Lookup CompRanges.csv
        LookupMarket --> LookupParity: Lookup EmployeeRoster.csv
        LookupParity --> ReturnData: Return raw data only
    }
    
    Research --> Judge: If Judge enabled
    Judge --> StreamResponse: Validated
    Research --> StreamResponse: Recommendation ready
    StreamResponse --> [*]: SSE stream to user
    
    note right of Coordinator
        Interprets natural language
        Extracts dynamic additional_context
        (counter offers, urgency, etc.)
        Maintains conversation context
        Normalizes user inputs
    end note
    
    note right of Research
        Calls DataCollector sub-agent
        Handles counter offer adjustments
        Generates recommendation
        Ensures zero hallucination
        Creates reasoning breakdown
    end note
    
    note right of DataCollector
        SUB-AGENT (not graph node)
        Exact-match lookups only
        No approximations
        Returns raw data
        Called conditionally by Research
    end note
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant LangGraph
    participant Coordinator
    participant Research
    participant DataCollector
    participant CSVFiles
    participant ContextStore
    
    User->>Frontend: Types message
    Frontend->>FastAPI: POST /api/chat/stream
    FastAPI->>ContextStore: Load candidate context
    ContextStore-->>FastAPI: Return context
    
    FastAPI->>LangGraph: Invoke workflow (message + context)
    LangGraph->>Coordinator: Process message
    
    Coordinator->>Coordinator: Parse & normalize
    Coordinator->>Coordinator: Check required fields
    
    alt Missing fields
        Coordinator->>LangGraph: Return question
        LangGraph->>FastAPI: Response
        FastAPI->>Frontend: SSE stream
        Frontend->>User: Display question
    else All fields present
        Coordinator->>Research: Structured data request
        Research->>DataCollector: Request market data
        DataCollector->>CSVFiles: Lookup CompRanges.csv
        CSVFiles-->>DataCollector: Market data
        DataCollector-->>Research: Raw market data
        
        Research->>DataCollector: Request internal parity
        DataCollector->>CSVFiles: Lookup EmployeeRoster.csv
        CSVFiles-->>DataCollector: Internal parity data
        DataCollector-->>Research: Raw parity data
        
        Research->>Research: Generate recommendation
        Research->>Research: Validate (zero hallucination)
        Research->>Research: Create reasoning
        
        Research->>LangGraph: Recommendation + reasoning
        LangGraph->>FastAPI: Response
        FastAPI->>ContextStore: Update context
        FastAPI->>Frontend: SSE stream (chunks)
        Frontend->>User: Display streaming response
    end
```

## Agent Responsibilities

### Coordinator Agent
- Interprets natural language user messages
- **Extracts dynamic additional_context** from messages (counter offers, salary expectations, urgency, special notes, etc.)
- **Accumulates additional_context** across conversation turns (merges new with existing)
- Maintains conversation context per candidate
- Normalizes user inputs (job title, location mapping, interview feedback)
- Validates required fields are collected (candidate_id, job_title, job_level, location, job_family, interview_feedback)
- Validates job level is valid (P1-P5)
- Routes workflow based on conversation state
- Handles greetings and off-topic messages appropriately

### Research Agent
- Receives structured data from Coordinator Agent
- **Conditionally invokes Data Collector Agent** (only if data is stale or missing)
- Reuses cached data if job_title/location match previous request
- **Processes additional_context** from Coordinator:
  - Adjusts recommendations for counter offers
  - Considers current salary for meaningful increases
  - Notes urgency in response
  - Applies special circumstances
- Generates compensation recommendation based on collected data
- **Handles counter offer scenarios**:
  - If counter offer is within market range: adjusts base salary to meet it
  - If counter offer exceeds market max: offers max + enhanced equity, flags for review
- Calculates accurate percentile, bonus, and total compensation
- Ensures zero hallucination (all values traceable to CSV data)
- Creates detailed reasoning breakdown with citations
- Flags guardrail violations

### Data Collector Agent (Sub-Agent)
- **Sub-agent invoked by Research Agent** (not a separate graph node)
- **Called conditionally**: only when Research Agent determines fresh data is needed
- Performs exact-match lookups in CompRanges.csv for market compensation
- Performs exact-match lookups in EmployeeRoster.csv for internal parity
- Returns raw data values only (no calculations or estimates)
- Never generates or approximates values
- Caches results for reuse within same job_title/location combination

### Judge Agent (Optional)
- **Enabled via settings** (`enable_judge_agent`)
- Validates recommendation against data
- Checks that base salary is within market min/max
- Verifies reasoning cites actual data sources
- Detects hallucinated numbers
- Flags recommendations that need review

## Data Sources

### CompRanges.csv (Market Compensation Data)
- Columns: Job Title, Location, Currency, Min, Max, Compensation Range
- Lookup: Exact match on Job Title + Location
- Returns: Min, Max, and Compensation Range as-is
- No approximations or fallbacks

### EmployeeRoster.csv (Internal Parity Data)
- Columns: Name, Job Title, Proficiency, Location, Compensation
- Lookup: Exact match on Job Title + Location
- Operations: Direct min/max, count
- Not allowed: Percentile estimation, trend analysis, predictive modeling

### Context Store (contexts.json)
- Location: `/data/contexts.json`
- Structure: Candidate ID → structured context object
- **Per-candidate storage**: Each candidate has their own context
- Contains: Required fields, additional_context, recommendation_history
- Retention: 60 days with auto-expiry

### Message Store (Per-User JSON files)
- Location: `/data/messages/user_<email>.json`
- **Per-user storage**: Messages organized by user, not candidate
- Structure: Array of message objects with candidate_id references
- Contains: User messages, assistant responses, timestamps, candidate associations
- Enables: Loading all user's messages, filtering by candidate

### Additional Context (Dynamic)
- Stored within candidate context as `additional_context` field
- **Dynamically extracted** by Coordinator from user messages
- **Accumulated** across conversation (new values merged with existing)
- Examples of captured information:
  - `counter_offer`: Competing offer amount
  - `current_salary`: Candidate's current compensation
  - `urgency`: Time-sensitive notes
  - `special_notes`: Any other relevant details
  - `relocation_needed`: Relocation requirements
  - `signing_bonus_request`: Requested signing bonus

### System Logs (CSV file)
- Location: `/data/logs/system_logs.csv`
- Tracks: All events (messages, responses, agent activity, recommendations, errors)

## Integration Map

### Current State (POC)

```mermaid
graph LR
    subgraph "Frontend"
        UI[Next.js UI]
    end
    
    subgraph "Backend"
        API[FastAPI API]
    end
    
    subgraph "Agent Layer"
        Agents[LangGraph Agents<br/>3 Graph Nodes + 1 Sub-Agent<br/>Coordinator → Research → Judge]
        DataCollector[DataCollector<br/>Sub-agent called by Research]
    end
    
    subgraph "Data Sources (Mock)"
        CompRanges[CompRanges.csv<br/>Mock Workday<br/>Market Compensation]
        EmployeeRoster[EmployeeRoster.csv<br/>Mock Greenhouse<br/>Internal Parity]
        ContextStore[contexts.json<br/>Per-Candidate Context]
        MessageStore[user_*.json<br/>Per-User Messages]
    end
    
    UI -->|HTTP/SSE| API
    API --> Agents
    Agents --> DataCollector
    DataCollector --> CompRanges
    DataCollector --> EmployeeRoster
    API -->|Read/Write| ContextStore
    API -->|Read/Write| MessageStore
    
    style UI fill:#e1f5ff
    style API fill:#fff4e1
    style Agents fill:#e8f5e9
    style DataCollector fill:#ffe0b2
    style CompRanges fill:#ffebee
    style EmployeeRoster fill:#ffebee
    style ContextStore fill:#ffebee
    style MessageStore fill:#ffebee
```

**Architecture Summary**:
- **3 Graph Nodes**: Coordinator, Research, Judge (optional)
- **1 Sub-Agent**: DataCollector (called by Research, not a graph node)
- **Per-User Messages**: Messages stored by user email, not candidate
- **Per-Candidate Context**: Context stored by candidate ID
- **Dynamic Context**: additional_context extracted and accumulated from messages

### Future Enhancements (V2)

```mermaid
graph LR
    subgraph "Frontend"
        UI[Next.js UI]
    end
    
    subgraph "Backend"
        API[FastAPI API]
    end
    
    subgraph "Agent Layer"
        Agents[LangGraph Agents<br/>Coordinator → Research<br/>+ Data Collector<br/>+ Judge Agent]
    end
    
    subgraph "External Integrations"
        Workday[Workday API<br/>Real Integration]
        Greenhouse[Greenhouse API<br/>Real Integration]
    end
    
    subgraph "Data Storage"
        Database[(PostgreSQL/MySQL)]
    end
    
    UI -->|HTTP/SSE| API
    API --> Agents
    Agents -->|Real-time API| Workday
    Agents -->|Real-time API| Greenhouse
    API -->|Read/Write| Database
    
    style UI fill:#e1f5ff
    style API fill:#fff4e1
    style Agents fill:#e8f5e9
    style Workday fill:#c8e6c9
    style Greenhouse fill:#c8e6c9
    style Database fill:#bbdefb
```

**Planned Enhancements**:
- **Judge Agent**: Additional validation layer for recommendations (future enhancement)
- **Workday API**: Real-time market compensation data integration
- **Greenhouse API**: Employee roster and candidate information integration
- **Database**: Replace JSON/CSV storage with relational database

## Technology Stack

### Frontend
- **Next.js 14+**: React-based web framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Zustand**: Client-side state management
- **Server-Sent Events (SSE)**: Real-time response streaming

### Backend
- **FastAPI**: Python web framework
- **LangGraph**: Agent orchestration and state management
- **Pydantic**: Data validation
- **Pandas**: CSV data processing

### Data Storage
- **JSON files**: Context persistence
- **CSV files**: Market data, internal parity, system logs

### Environment
- **Python 3.10+**: Runtime environment
- **Virtual environment**: `/backend/.venv`
- **Environment variables**: `/backend/.env` (API keys, configuration)
