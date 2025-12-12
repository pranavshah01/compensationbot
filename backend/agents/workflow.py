"""
Simplified Coordinator Agent Workflow for Compensation Recommendations.
Clean, linear logic with clear separation of concerns.
"""
from typing import TypedDict, Literal, Optional, Dict, Any, Set, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import re
import asyncio
import logging
from datetime import datetime, timezone
from config import settings
from data.access import data_access
from context.store import context_store
from context.user_store import user_context_store
from messages import message_store
from models import UserType

logger = logging.getLogger("compagent")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ============================================================================
# CONSTANTS
# ============================================================================

REQUIRED_FIELDS = ["candidate_id", "job_title", "job_level", "location", "job_family", "interview_feedback"]

FIELD_DISPLAY_NAMES = {
    "candidate_id": "Candidate ID",
    "job_title": "Job Title",
    "job_level": "Job Level (P1-P5)",
    "location": "Location",
    "job_family": "Job Family",
    "interview_feedback": "Interview Panel Feedback (Must Hire/Strong Hire/Hire)"
}

VALID_LEVELS = {"P1", "P2", "P3", "P4", "P5"}
VALID_FEEDBACK = {"Must Hire", "Strong Hire", "Hire"}

# Compensation defaults by job level
BONUS_BY_LEVEL = {"P5": 20, "P4": 15, "P3": 10, "P2": 8, "P1": 5}
EQUITY_BY_LEVEL = {"P5": 100000, "P4": 60000, "P3": 30000, "P2": 20000, "P1": 10000}
DEFAULT_BONUS = 10
DEFAULT_EQUITY = 30000

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    message: str
    candidate_id: Optional[str]
    context: Dict[str, Any]
    research_data: Dict[str, Any]  # Populated by Data Collector (called from Research)
    recommendation: Dict[str, Any]
    response: str
    next_step: Literal["collect", "research", "judge", "respond", "end"]
    user_email: Optional[str]
    user_type: Optional[str]
    message_history: List[Dict[str, Any]]
    missing_fields: List[str]
    extracted_fields: Dict[str, Any]

# ============================================================================
# LLM SETUP
# ============================================================================

def get_llm():
    try:
        return ChatOpenAI(model=settings.openai_model, temperature=0, openai_api_key=settings.openai_api_key)
    except:
        return ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, google_api_key=settings.gemini_api_key)

def get_research_llm():
    try:
        return ChatOpenAI(model=settings.openai_model, temperature=0.2, openai_api_key=settings.openai_api_key)
    except:
        return ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.2, google_api_key=settings.gemini_api_key)

def get_judge_llm():
    return ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, google_api_key=settings.gemini_api_key)

llm = get_llm()

# ============================================================================
# UTILITIES
# ============================================================================

def extract_candidate_id(text: str) -> Optional[str]:
    """Extract CAND-XXX format ID from text."""
    match = re.search(r'CAND-([A-Z0-9_-]+)', text, re.IGNORECASE)
    return f"CAND-{match.group(1).upper()}" if match else None

def get_missing_fields(context: Dict[str, Any]) -> List[str]:
    """Return list of missing required fields."""
    return [f for f in REQUIRED_FIELDS if not context.get(f)]

def get_friendly_names(fields: List[str]) -> List[str]:
    """Convert field names to user-friendly display names."""
    return [FIELD_DISPLAY_NAMES.get(f, f) for f in fields]

def normalize_feedback(value: str) -> Optional[str]:
    """Normalize interview feedback to standard values."""
    if not value:
        return None
    lower = value.lower().replace("-", " ").replace("_", " ").strip()
    # Check negative cases first to avoid false positives
    if "no hire" in lower or "do not hire" in lower or "don't hire" in lower or "not hire" in lower:
        return None  # Invalid feedback - don't proceed
    if "must hire" in lower:
        return "Must Hire"
    if "strong hire" in lower:
        return "Strong Hire"
    # Require exact match or close to avoid false positives like "we should hire"
    if lower == "hire" or lower.endswith(" hire"):
        return "Hire"
    return None

def extract_json(text: str) -> Optional[dict]:
    """Extract JSON object from text, handling nested structures."""
    if not text:
        return None
    try:
        # Find the first '{' and match it with the correct '}'
        start = text.find('{')
        if start < 0:
            return None
        
        # Count braces to find matching end
        depth = 0
        end = -1
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end > start:
            return json.loads(text[start:end+1])
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
    except Exception as e:
        logger.warning(f"Error extracting JSON: {e}")
    return None

# ============================================================================
# COORDINATOR PROMPT (DYNAMIC CONTEXT EXTRACTION)
# ============================================================================

COORDINATOR_PROMPT = """You are a compensation recommendation assistant. You ONLY handle compensation-related requests.

MESSAGE HANDLING RULES:
1. GREETINGS (hi, hello, hey, etc.) → Respond warmly and naturally, ask how you can help with compensation
2. OFF-TOPIC (weather, jokes, coding help, anything not about compensation) → Politely say: "I can only help with compensation recommendations for candidates. Is there a candidate you'd like me to help with?"
3. COMPENSATION REQUESTS → Collect required info and provide recommendations

REQUIRED FIELDS (must have all 6 before generating recommendation):
- candidate_id (CAND-XXX format)
- job_title
- job_level (P1-P5)
- location (LAX, SEA, STL, DUB, SHA, SYD, SIN)
- job_family (Engineering, Finance, Legal, HR, Sales, Marketing, Operations, Executive)
- interview_feedback (Must Hire, Strong Hire, Hire)

ADDITIONAL CONTEXT - Extract ANY relevant compensation info mentioned in the message:
Examples of what to extract (not limited to these):
- Competing/counter offers and amounts
- Candidate's salary expectations
- Current compensation
- Signing bonus requests
- Equity preferences
- Relocation needs or costs
- Start date urgency
- Retention risk concerns
- Special skills or certifications
- Years of experience
- Previous negotiations
- Any other relevant details

IMPORTANT: Every new piece of information should be captured in additional_context.

LOCATION MAPPING: LA/Los Angeles→LAX, Seattle→SEA, St. Louis→STL, Dublin→DUB, Shanghai→SHA, Sydney→SYD, Singapore→SIN

CURRENT CONTEXT:
{context_json}

EXISTING ADDITIONAL CONTEXT (accumulated from previous messages):
{additional_context_json}

CONVERSATION HISTORY:
{history_text}

USER MESSAGE: {message}

INSTRUCTIONS:
1. Determine if this is a greeting, off-topic, or compensation-related
2. For GREETINGS → Friendly response asking how you can help
3. For OFF-TOPIC → Politely decline and redirect
4. For COMPENSATION → Extract ALL relevant info
5. Merge any new additional context with existing additional_context (don't lose previous info)
6. If all 6 required fields are complete AND user wants recommendation → output ACTION: RESEARCH

RESPONSE FORMAT - Output JSON block with:
{{
  "candidate_id": "CAND-XXX" or null,
  "job_title": "..." or null,
  "job_level": "P1-P5" or null,
  "location": "LAX/SEA/etc" or null,
  "job_family": "..." or null,
  "interview_feedback": "Must Hire/Strong Hire/Hire" or null,
  "additional_context": {{
    // Include ALL accumulated context - merge new with existing
    // Examples:
    // "counter_offer": 350000,
    // "current_salary": 280000,
    // "relocation_needed": true,
    // "urgency": "competing offer expires Friday",
    // "special_notes": "candidate has rare ML expertise"
  }}
}}

Then write your conversational response.
If ready for research, add "ACTION: RESEARCH" at the end.

Example with additional context:

{{"candidate_id": "CAND-001", "job_title": "Senior Engineer", "job_level": "P4", "location": "SEA", "job_family": "Engineering", "interview_feedback": "Must Hire", "additional_context": {{"counter_offer": 350000, "current_salary": 280000, "urgency": "needs response by Friday"}}}}

Understood! The candidate has a counter offer of $350,000 and currently makes $280,000. I'll factor this into a competitive recommendation.

ACTION: RESEARCH
"""

# ============================================================================
# COORDINATOR AGENT
# ============================================================================

async def coordinator_agent(state: AgentState) -> dict:
    """
    Simplified coordinator with clear linear flow:
    1. Resolve candidate ID
    2. Load/merge context
    3. Check recruiter restrictions
    4. Call LLM
    5. Extract fields from response
    6. Validate completeness
    7. Route to research or respond
    """
    message = (state.get("message") or "").strip()
    user_email = state.get("user_email")
    user_type = state.get("user_type")
    
    # -------------------------------------------------------------------------
    # STEP 1: Resolve candidate ID
    # -------------------------------------------------------------------------
    extracted_cid = extract_candidate_id(message)
    current_cid = user_context_store.get_current_candidate(user_email)
    
    candidate_id = (
        extracted_cid or
        state.get("candidate_id") or
        current_cid or
        message_store.get_most_recent_candidate_id(user_email)
    )
    
    # Let LLM handle all messages (greetings, off-topic, and compensation requests)
    # No hardcoded responses - LLM will respond appropriately based on prompt
    
    # -------------------------------------------------------------------------
    # STEP 2: Load context
    # -------------------------------------------------------------------------
    context = {}
    if candidate_id:
        stored = context_store.get_context(candidate_id)
        if stored and stored.state.value == "active":
            context = stored.model_dump()
        
        # Update user's current candidate
        if candidate_id != current_cid:
            user_context_store.set_current_candidate(user_email, candidate_id)
    
    # Load message history for this user (optionally filtered by candidate)
    message_history = message_store.get_messages(user_email, limit=10, candidate_id=candidate_id) if user_email else []
    
    # -------------------------------------------------------------------------
    # STEP 3: Recruiter restrictions
    # -------------------------------------------------------------------------
    if user_type == UserType.RECRUITMENT_TEAM and candidate_id:
        existing = context_store.get_context(candidate_id)
        if not existing or not existing.recommendation_history:
            return {
                **state,
                "response": "I can only help you with candidates that have existing recommendations from the Compensation Team.",
                "next_step": "respond"
            }
    
    # -------------------------------------------------------------------------
    # STEP 4: Build prompt and call LLM
    # -------------------------------------------------------------------------
    metadata = data_access.get_metadata()
    
    context_json = json.dumps({
        "candidate_id": context.get("candidate_id") or candidate_id,
        "job_title": context.get("job_title"),
        "job_level": context.get("job_level"),
        "location": context.get("location"),
        "job_family": context.get("job_family"),
        "interview_feedback": context.get("interview_feedback")
    }, indent=2)
    
    # Get existing additional_context (accumulated from previous messages)
    existing_additional_context = context.get("additional_context", {})
    additional_context_json = json.dumps(existing_additional_context, indent=2) if existing_additional_context else "{}"
    
    history_text = ""
    for msg in message_history[-5:]:
        if msg.get("message"):
            history_text += f"User: {msg['message']}\n"
        if msg.get("response"):
            history_text += f"Assistant: {msg['response']}\n"
    
    prompt = COORDINATOR_PROMPT.format(
        context_json=context_json,
        additional_context_json=additional_context_json,
        history_text=history_text or "None",
        message=message
    )
    
    try:
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        response_text = response.content or ""
    except Exception as e:
        return {**state, "response": f"Error: {e}", "next_step": "respond"}
    
    # -------------------------------------------------------------------------
    # STEP 5: Parse LLM response
    # -------------------------------------------------------------------------
    has_action_research = bool(re.search(r'ACTION\s*:\s*RESEARCH', response_text, re.IGNORECASE))
    
    # Extract user-facing response (before JSON)
    user_response = re.sub(r'\{[\s\S]*\}', '', response_text)
    user_response = re.sub(r'ACTION\s*:\s*RESEARCH', '', user_response, flags=re.IGNORECASE)
    user_response = user_response.strip()
    
    # Extract JSON
    extracted = extract_json(response_text)
    
    # -------------------------------------------------------------------------
    # STEP 6: Merge extracted fields into context
    # -------------------------------------------------------------------------
    if extracted:
        # Extract required fields
        for field in REQUIRED_FIELDS:
            value = extracted.get(field)
            if value and str(value).strip().lower() not in ("null", "none", ""):
                context[field] = value
        
        # Merge additional_context (accumulate, don't replace)
        new_additional = extracted.get("additional_context", {})
        if new_additional and isinstance(new_additional, dict):
            existing_additional = context.get("additional_context", {})
            if not isinstance(existing_additional, dict):
                existing_additional = {}
            
            # Merge new into existing (new values override for same keys)
            merged_additional = {**existing_additional, **new_additional}
            context["additional_context"] = merged_additional
            
            if new_additional:
                logger.info(f"Coordinator: Merged additional_context: {list(new_additional.keys())}")
    
    # Ensure candidate_id is set
    context["candidate_id"] = context.get("candidate_id") or candidate_id
    
    # Normalize feedback
    if context.get("interview_feedback"):
        normalized = normalize_feedback(context["interview_feedback"])
        if normalized:
            context["interview_feedback"] = normalized
    
    # -------------------------------------------------------------------------
    # STEP 7: Check completeness and route
    # -------------------------------------------------------------------------
    missing = get_missing_fields(context)
    
    # Save context only if we have a candidate
    if context.get("candidate_id"):
        try:
            context_store.save_context(context["candidate_id"], context, user_email or "system")
        except Exception as e:
            logger.warning(f"Failed to save context for {context.get('candidate_id')}: {e}")
    
    # If no candidate_id in context, this is likely a greeting or off-topic
    # Use LLM's response directly
    if not context.get("candidate_id"):
        return {
            **state,
            "candidate_id": None,
            "context": {},
            "response": user_response or "Hi! How can I help you with compensation today?",
            "next_step": "respond"
        }
    
    # If missing fields and user provided some candidate info, ask for missing
    if missing:
        friendly = get_friendly_names(missing)
        return {
            **state,
            "candidate_id": context.get("candidate_id"),
            "context": context,
            "missing_fields": missing,
            "response": user_response or f"I still need: {', '.join(friendly)}. Could you provide these?",
            "next_step": "respond"
        }
    
    # Validate job level before proceeding
    job_level = context.get("job_level")
    if job_level and job_level not in VALID_LEVELS:
        return {
            **state,
            "candidate_id": context.get("candidate_id"),
            "context": context,
            "response": f"Invalid job level '{job_level}'. Must be one of: {', '.join(sorted(VALID_LEVELS))}. Please provide a valid job level.",
            "next_step": "respond"
        }
    
    # All fields present
    if has_action_research or any(kw in message.lower() for kw in ["recommendation", "compensation", "offer", "salary"]):
        # Ready for research
        return {
            **state,
            "candidate_id": context.get("candidate_id"),
            "context": context,
            "research_data": context,
            "response": "",
            "next_step": "research"
        }
    
    # Just acknowledging info
    return {
        **state,
        "candidate_id": context.get("candidate_id"),
        "context": context,
        "response": user_response or "Got it! Let me know when you're ready for a compensation recommendation.",
        "next_step": "respond"
    }

# ============================================================================
# DATA COLLECTOR AGENT (Sub-agent called by Research)
# ============================================================================

class DataCollectorAgent:
    """
    Data Collector Agent - Responsible for gathering compensation data from sources.
    
    This is a sub-agent that is invoked by the Research Agent when fresh data is needed.
    It collects data from:
    - CompRanges.csv: Market compensation ranges by job title and location
    - EmployeeRoster.csv: Internal parity data for comparable employees
    
    The Research Agent will skip calling this if:
    - research_data already exists in state (from previous recommendation)
    - Data was recently collected for the same job_title/location combination
    """
    
    @staticmethod
    def is_data_fresh(research_data: Dict[str, Any], job_title: str, location: str) -> bool:
        """
        Check if existing research data is still valid for the given job/location.
        Returns True if data can be reused, False if fresh collection needed.
        """
        if not research_data:
            return False
        
        # Check if data exists and matches current request
        cached_job = research_data.get("job_title")
        cached_loc = research_data.get("location")
        
        if cached_job and cached_loc:
            if cached_job.lower() == job_title.lower() and cached_loc.upper() == location.upper():
                # Data exists for same job/location - check if market data is available
                market = research_data.get("market_data", {})
                if market.get("available") is not None:  # Data was collected (even if no match)
                    logger.info(f"DataCollector: Reusing cached data for {job_title} in {location}")
                    return True
        
        return False
    
    @staticmethod
    async def collect(job_title: str, location: str) -> dict:
        """
        Collect market and parity data from CSV sources.
        
        Args:
            job_title: The job title to look up (e.g., "Senior Software Engineer")
            location: The location code (e.g., "LAX", "SEA")
            
        Returns:
            Dictionary containing:
            - job_title: The requested job title
            - location: The requested location
            - market_data: Market compensation range from CompRanges.csv
            - internal_parity: Internal parity data from EmployeeRoster.csv
        """
        logger.info(f"DataCollector: Collecting data for {job_title} in {location}")
        
        # Collect from both sources
        market_result = data_access.get_market_compensation(job_title, location)
        parity_result = data_access.get_internal_parity(job_title, location)
        
        result = {
            "job_title": job_title,
            "location": location,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "market_data": {
                "source": "CompRanges.csv",
                "data": market_result.model_dump() if market_result else None,
                "available": market_result is not None
            },
            "internal_parity": {
                "source": "EmployeeRoster.csv", 
                "data": parity_result.model_dump() if parity_result else None,
                "available": parity_result is not None
            }
        }
        
        if market_result:
            logger.info(f"DataCollector: Found market data - ${market_result.min:,} to ${market_result.max:,}")
        else:
            logger.warning(f"DataCollector: No market data found for {job_title} in {location}")
            
        if parity_result:
            logger.info(f"DataCollector: Found internal parity - {parity_result.count} employees")
        else:
            logger.info(f"DataCollector: No internal parity data for {job_title} in {location}")
        
        return result


# Convenience function for backward compatibility
async def collect_compensation_data(job_title: str, location: str) -> dict:
    """Collect market and parity data. Delegates to DataCollectorAgent."""
    return await DataCollectorAgent.collect(job_title, location)

# ============================================================================
# RESEARCH AGENT (Simplified)
# ============================================================================

RESEARCH_PROMPT = """You are a compensation research agent. ONLY use data provided - NO hallucination.

CONTEXT (includes additional_context with all accumulated information):
{context_json}

DATA:
{data_json}

RULES:
1. If market_data.available is False → return status "no_data" with NO compensation numbers
2. Base salary MUST be within market min/max range from CompRanges.csv
3. Calculate percentile: ((base_salary - min) / (max - min)) * 100
4. Interview feedback affects percentile target: Must Hire→75-90th, Strong Hire→50-75th, Hire→25-50th
5. Job level affects bonus/equity: P5→20% bonus/$100k equity, P4→15%/$60k, P3→10%/$30k, P2→8%/$20k, P1→5%/$10k
6. ALWAYS cite exact values from data sources in reasoning

ADDITIONAL CONTEXT RULES - Check additional_context and factor in:
- counter_offer: Try to meet/exceed if within market range; if exceeds max, use max + enhanced equity
- current_salary: Ensure meaningful increase (typically 10-20% minimum)
- urgency: Note in response if time-sensitive
- special_notes: Factor in any special circumstances
- Any other relevant context provided

OUTPUT (JSON only, no other text):
{{
  "status": "approved"|"needs_review"|"no_data",
  "data_status": "OK"|"NO_MATCH_IN_DATA",
  "market_compensation": {{"min": number, "max": number, "currency": "USD"}} or null,
  "internal_parity": {{"min": number, "max": number, "count": number}} or null,
  "recommendation": {{
    "base_salary": number,
    "base_salary_percentile": number (0-100, calculated as ((base-min)/(max-min))*100),
    "bonus_percentage": number,
    "equity_amount": number,
    "total_compensation": number (base + base*bonus% + equity),
    "reasoning": {{
      "market_data_citation": "CompRanges.csv: [Job Title] in [Location] range $X - $Y",
      "internal_parity_citation": "EmployeeRoster.csv: N employees, range $X - $Y" or "No internal parity data",
      "percentile_justification": "X percentile chosen because [interview feedback] rating indicates [reasoning]",
      "bonus_justification": "X% bonus for [level] level per company policy",
      "equity_justification": "$X equity for [level] level per company policy"
    }}
  }},
  "response_text": "MUST include: 1) Total compensation package ($X total = $base + $bonus + $equity), 2) Breakdown of each component, 3) Brief justification citing data source. Example: 'For [Candidate], I recommend a total compensation of $355,600 consisting of: Base Salary: $213,000 (85th percentile of market range $175k-$237k per CompRanges.csv), Bonus: $42,600 (20% for P5 level), Equity: $100,000. This reflects the Must Hire interview feedback.'"
}}
"""

def parse_money(s) -> Optional[float]:
    """Parse '$150k', '150000', '1.5m' → float. Returns None for invalid input."""
    if s is None or s == "":
        return None
    try:
        t = str(s).lower().replace(',', '').replace('$', '').strip()
        if not t:
            return None
        if t.endswith('k'):
            return float(t[:-1]) * 1000
        if t.endswith('m'):
            return float(t[:-1]) * 1_000_000
        result = float(t)
        return result if result > 0 else None  # Treat 0 or negative as invalid
    except (ValueError, TypeError):
        return None

async def research_agent(state: AgentState) -> dict:
    """
    Research Agent - Generates compensation recommendations based on data.
    
    This agent:
    1. Checks if data collection is needed (calls DataCollectorAgent if so)
    2. Analyzes market data and internal parity
    3. Generates compensation recommendation with reasoning
    4. Routes to Judge Agent for validation (if enabled)
    
    Data Collection Logic:
    - If research_data exists AND matches current job_title/location → reuse cached data
    - Otherwise → call DataCollectorAgent to fetch fresh data
    """
    research_data = state.get("research_data") or {}
    context = state.get("context") or {}
    candidate_id = state.get("candidate_id")
    user_email = state.get("user_email")
    
    job_title = research_data.get("job_title") or context.get("job_title")
    location = research_data.get("location") or context.get("location")
    
    if not job_title or not location:
        return {**state, "response": "Missing job title or location.", "next_step": "respond"}
    
    # Check if we need to collect fresh data (DataCollectorAgent)
    if not DataCollectorAgent.is_data_fresh(research_data, job_title, location):
        logger.info(f"Research: Invoking DataCollectorAgent for {job_title} in {location}")
        data = await DataCollectorAgent.collect(job_title, location)
        research_data.update(data)
    else:
        logger.info(f"Research: Using existing data for {job_title} in {location}")
    
    market = research_data.get("market_data", {})
    
    # No market data → can't recommend
    if not market.get("available"):
        return {
            **state,
            "research_data": research_data,
            "recommendation": {"status": "no_data", "data_status": "NO_MATCH_IN_DATA"},
            "response": f"No market data found for {job_title} in {location}. Please verify the job title and location.",
            "next_step": "respond"
        }
    
    # Call LLM for recommendation
    prompt = RESEARCH_PROMPT.format(
        context_json=json.dumps(context, indent=2, default=str),
        data_json=json.dumps(research_data, indent=2, default=str)
    )
    
    try:
        response = await get_research_llm().ainvoke([SystemMessage(content=prompt)])
        result = extract_json(response.content)
    except Exception as e:
        logger.exception("Research LLM error")
        return {**state, "response": f"Research error: {e}", "next_step": "respond"}
    
    if not result:
        return {**state, "response": "Could not parse recommendation.", "next_step": "respond"}
    
    # Normalize recommendation values
    rec = result.get("recommendation", {})
    level = context.get("job_level", "P3")
    market_data = market.get("data", {})
    
    # Get additional_context (dynamic - can contain anything)
    additional_context = context.get("additional_context", {})
    counter_offer = additional_context.get("counter_offer")
    logger.info(f"Research: Context additional_context = {additional_context}")
    logger.info(f"Research: Counter offer from context = {counter_offer}")
    
    # Ensure numeric values - use constants for defaults
    rec["base_salary"] = parse_money(rec.get("base_salary"))
    rec["bonus_percentage"] = float(rec.get("bonus_percentage") or BONUS_BY_LEVEL.get(level, DEFAULT_BONUS))
    parsed_equity = parse_money(rec.get("equity_amount"))
    rec["equity_amount"] = parsed_equity if parsed_equity is not None else EQUITY_BY_LEVEL.get(level, DEFAULT_EQUITY)
    logger.info(f"Research: Parsed rec base_salary={rec.get('base_salary')}, counter_offer={counter_offer}")
    
    # Calculate percentile from market data
    market_min = float(market_data.get("Min") or market_data.get("min") or 0) if market_data else 0
    market_max = float(market_data.get("Max") or market_data.get("max") or 0) if market_data else 0
    
    # Ensure we have a base salary - if LLM didn't provide one, calculate based on interview feedback
    if not rec.get("base_salary") and market_max > 0:
        interview_fb = context.get("interview_feedback", "").lower()
        if "must" in interview_fb:
            rec["base_salary"] = round(market_min + (market_max - market_min) * 0.85, 0)  # 85th percentile
        elif "strong" in interview_fb:
            rec["base_salary"] = round(market_min + (market_max - market_min) * 0.75, 0)  # 75th percentile
        else:
            rec["base_salary"] = round(market_min + (market_max - market_min) * 0.50, 0)  # 50th percentile
        logger.info(f"Research: Calculated base salary ${rec['base_salary']:,.0f} based on interview feedback")
    
    # Handle counter offer from additional_context - try to meet or exceed it within market constraints
    if counter_offer and rec.get("base_salary"):
        counter_offer_value = parse_money(counter_offer)
        if counter_offer_value > 0:
            logger.info(f"Research: Adjusting for counter offer of ${counter_offer_value:,.0f}")
            rec["counter_offer"] = counter_offer_value
            
            # Calculate what base salary would be needed
            # Total = base + base*bonus% + equity
            # If counter_offer = total, then base = (counter_offer - equity) / (1 + bonus%)
            target_base = (counter_offer_value - rec["equity_amount"]) / (1 + rec["bonus_percentage"] / 100)
            
            if target_base <= market_max:
                # We can meet the counter offer within market range
                rec["base_salary"] = round(max(market_min, target_base), 0)
                result["status"] = "approved"
                logger.info(f"Research: Adjusted base to ${rec['base_salary']:,.0f} to meet counter offer")
            else:
                # Counter offer exceeds what we can do - offer max and flag for review
                rec["base_salary"] = market_max
                
                # Calculate gap before adding equity boost
                original_equity = rec["equity_amount"]
                max_total_before_boost = market_max * (1 + rec["bonus_percentage"] / 100) + original_equity
                gap = counter_offer_value - max_total_before_boost
                
                # Add up to $50k extra equity to bridge the gap
                equity_boost = 0
                if gap > 0:
                    equity_boost = min(gap, 50000)
                    rec["equity_amount"] = original_equity + equity_boost
                
                remaining_gap = gap - equity_boost
                result["status"] = "needs_review"
                
                if equity_boost > 0:
                    rec["counter_offer_note"] = f"Counter offer of ${counter_offer_value:,} exceeds market max. Added ${equity_boost:,.0f} extra equity. Remaining gap: ${remaining_gap:,.0f}"
                else:
                    rec["counter_offer_note"] = f"Counter offer of ${counter_offer_value:,} exceeds our maximum offer. Gap: ${gap:,.0f}"
                
                logger.warning(f"Research: Counter offer ${counter_offer_value:,.0f} exceeds market max ${market_max:,.0f}. Gap: ${gap:,.0f}, Equity boost: ${equity_boost:,.0f}")
    
    # Store additional_context in recommendation for reference
    if additional_context:
        rec["additional_context_applied"] = additional_context
    
    if rec.get("base_salary") and market_max > market_min:
        percentile = ((rec["base_salary"] - market_min) / (market_max - market_min)) * 100
        rec["base_salary_percentile"] = round(max(0, min(100, percentile)), 1)  # Clamp to 0-100
    else:
        # Default to 50th percentile if no data or invalid
        rec["base_salary_percentile"] = rec.get("base_salary_percentile") or 50
    
    # Calculate total comp
    if rec.get("base_salary"):
        bonus_amount = rec["base_salary"] * rec["bonus_percentage"] / 100
        rec["bonus_amount"] = round(bonus_amount, 2)
        rec["total_compensation"] = round(rec["base_salary"] + bonus_amount + rec["equity_amount"], 2)
    
    # Store market data citations for frontend (using already extracted values)
    rec["market_range"] = {
        "min": market_min,
        "max": market_max,
        "source": "CompRanges.csv"
    }
    
    # Store internal parity citations
    parity = research_data.get("internal_parity", {})
    if parity.get("available") and parity.get("data"):
        parity_data = parity["data"]
        rec["internal_parity"] = {
            "min": float(parity_data.get("Min") or parity_data.get("min") or 0),
            "max": float(parity_data.get("Max") or parity_data.get("max") or 0),
            "count": int(parity_data.get("Count") or parity_data.get("count") or 0),
            "source": "EmployeeRoster.csv"
        }
    
    result["recommendation"] = rec
    
    # Generate accurate response_text using backend-calculated values (not LLM's potentially wrong math)
    job_title = context.get("job_title", "the candidate")
    interview_fb = context.get("interview_feedback") or context.get("proficiency") or "Hire"
    
    # Build response text - include counter offer handling if applicable
    counter_offer_text = ""
    status = result.get("status", "approved")
    
    if rec.get("counter_offer"):
        counter_value = rec["counter_offer"]
        our_total = rec.get("total_compensation", 0)
        
        if status == "needs_review" or rec.get("counter_offer_note"):
            # We couldn't fully match the counter offer
            gap = counter_value - our_total
            counter_offer_text = (
                f"\n\n⚠️ **Counter Offer Analysis:** The candidate's counter offer of ${counter_value:,.0f} "
                f"exceeds our maximum market-based offer of ${our_total:,.0f} (gap: ${gap:,.0f}). "
                f"Our offer is at the top of the approved market range. "
                f"**Recommendation:** This requires VP/executive approval to exceed market guidelines, "
                f"or consider non-monetary benefits (signing bonus, additional PTO, remote work flexibility, "
                f"accelerated review timeline) to bridge the gap."
            )
        else:
            counter_offer_text = f" This revised recommendation addresses the counter offer of ${counter_value:,.0f}."
    
    response_text = (
        f"For {candidate_id or 'this candidate'}, I recommend a total compensation of "
        f"${rec.get('total_compensation', 0):,.0f} consisting of: "
        f"Base Salary: ${rec.get('base_salary', 0):,.0f} "
        f"({round(rec.get('base_salary_percentile', 50))}th percentile of market range "
        f"${market_min:,.0f}-${market_max:,.0f} per CompRanges.csv), "
        f"Bonus: ${rec.get('bonus_amount', 0):,.0f} ({rec.get('bonus_percentage', 0):.0f}% for {level} level), "
        f"Equity: ${rec.get('equity_amount', 0):,.0f}. "
        f"This reflects the {interview_fb} interview feedback.{counter_offer_text}"
    )
    result["response_text"] = response_text
    
    # Save recommendation
    if candidate_id:
        try:
            ctx = context_store.get_context(candidate_id)
            if ctx:
                ctx_dict = ctx.model_dump() if hasattr(ctx, 'model_dump') else dict(ctx)
                # Prepare context snapshot for history
                context_snapshot = {
                    "job_title": context.get("job_title"),
                    "job_level": context.get("job_level"),
                    "location": context.get("location"),
                    "interview_feedback": context.get("interview_feedback") or context.get("proficiency"),
                    "job_family": context.get("job_family"),
                }
                ctx_dict.setdefault("recommendation_history", []).append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context_snapshot": context_snapshot,
                    "recommendation": result
                })
                ctx_dict["recommendation"] = result
                context_store.save_context(candidate_id, ctx_dict, user_email or "system")
        except Exception as e:
            logger.warning(f"Error saving recommendation to context: {e}")
    
    return {
        **state,
        "research_data": research_data,
        "recommendation": result,
        "response": result.get("response_text", "Recommendation complete."),
        "next_step": "judge" if settings.enable_judge_agent else "respond"
    }

# ============================================================================
# JUDGE AGENT (Simplified)
# ============================================================================

JUDGE_PROMPT = """Validate this compensation recommendation against the data.

DATA: {data_json}

RECOMMENDATION: {recommendation_json}

CHECK:
1. Base salary within market min/max?
2. Reasoning cites actual data sources?
3. No hallucinated numbers?

OUTPUT (JSON only):
{{"approved": true|false, "issues": [], "feedback": "..."}}
"""

async def judge_agent(state: AgentState) -> dict:
    """Validate recommendation against data."""
    if not settings.enable_judge_agent:
        return {**state, "next_step": "respond"}
    
    recommendation = state.get("recommendation", {})
    research_data = state.get("research_data", {})
    
    if not recommendation:
        return {**state, "next_step": "respond"}
    
    prompt = JUDGE_PROMPT.format(
        data_json=json.dumps({"market": research_data.get("market_data"), "parity": research_data.get("internal_parity")}, indent=2),
        recommendation_json=json.dumps(recommendation, indent=2)
    )
    
    try:
        response = await get_judge_llm().ainvoke([SystemMessage(content=prompt)])
        result = extract_json(response.content)
        if result:
            recommendation["judge_validation"] = result
            if not result.get("approved"):
                recommendation["status"] = "needs_review"
    except Exception as e:
        logger.warning(f"Judge agent error (continuing without validation): {e}")
    
    return {
        **state,
        "recommendation": recommendation,
        "response": recommendation.get("response_text", "Recommendation complete."),
        "next_step": "respond"
    }

# ============================================================================
# WORKFLOW GRAPH
# ============================================================================
#
# Architecture: 3 Graph Nodes + 1 Sub-Agent
#
#   ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
#   │ Coordinator │ ──► │   Research   │ ──► │    Judge    │
#   │   (Entry)   │     │   (+ Data    │     │ (Validation)│
#   └─────────────┘     │   Collector) │     └─────────────┘
#                       └──────────────┘
#
# - Coordinator: Collects candidate info, routes to Research when complete
# - Research: Calls DataCollectorAgent if needed, generates recommendation
# - DataCollectorAgent: Sub-agent that fetches from CompRanges.csv & EmployeeRoster.csv
# - Judge: Validates recommendation against data (optional, via settings)
#
# Data Collection Logic:
# - If research_data exists AND matches job_title/location → reuse (skip DataCollector)
# - Otherwise → Research invokes DataCollectorAgent to fetch fresh data
#
# ============================================================================

def build_workflow():
    workflow = StateGraph(AgentState)
    
    # 3 main graph nodes (DataCollector is sub-agent called by Research)
    workflow.add_node("coordinator", coordinator_agent)
    workflow.add_node("research", research_agent)
    workflow.add_node("judge", judge_agent)
    
    workflow.set_entry_point("coordinator")
    
    # Coordinator routes to research or ends
    workflow.add_conditional_edges(
        "coordinator",
        lambda s: s.get("next_step", "respond"),
        {"research": "research", "respond": END, "end": END}
    )
    
    # Research routes to judge or ends
    workflow.add_conditional_edges(
        "research",
        lambda s: s.get("next_step", "respond"),
        {"judge": "judge", "respond": END, "end": END}
    )
    
    # Judge always ends
    workflow.add_edge("judge", END)
    
    return workflow.compile()

# Single workflow instance
agent_workflow = build_workflow()

async def run_workflow(message: str, user_email: str, user_type: str = "comp_team") -> dict:
    """Run the compensation workflow."""
    current_cid = user_context_store.get_current_candidate(user_email)
    context = {}
    if current_cid:
        stored = context_store.get_context(current_cid)
        if stored:
            context = stored.model_dump()
    
    initial_state: AgentState = {
        "message": message,
        "candidate_id": current_cid,
        "context": context,
        "research_data": {},
        "recommendation": {},
        "response": "",
        "next_step": "collect",
        "user_email": user_email,
        "user_type": user_type,
        "message_history": [],
        "missing_fields": [],
        "extracted_fields": {}
    }
    
    return await agent_workflow.ainvoke(initial_state)
