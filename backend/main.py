"""FastAPI main application."""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from typing import Optional
import asyncio
import uuid
import json
import time
import logging

from models import (
    LoginRequest, LoginResponse, ChatRequest, ContextResetRequest,
    FeedbackRequest, FeedbackResponse, UserType
)
from auth import authenticate_user, create_access_token, get_user_from_token
from context import context_store, user_context_store
from utils import system_logger
from agents import agent_workflow, AgentState
from messages import message_store

# Configure logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Compensation Recommendation Assistant API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(authorization: str = Header(None)) -> dict:
    """Get current authenticated user from token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


@app.post("/api/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = authenticate_user(login_request.email, login_request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user["email"]})
    
    # Get current candidate for user
    current_candidate_id = user_context_store.get_current_candidate(user["email"])
    
    # Log login
    system_logger.log(
        event_type="Login",
        user_email=user["email"],
        user_type=user["user_type"],
        status="Success"
    )
    
    return LoginResponse(
        token=token,
        user_type=user["user_type"],
        user_email=user["email"],
        current_candidate_id=current_candidate_id
    )


@app.post("/api/chat/stream")
async def chat_stream(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Stream chat responses using SSE."""
    session_id = chat_request.session_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    user_email = current_user["email"]
    
    # Get current candidate - priority order:
    # 1. From request
    # 2. From user context (current session)
    # 3. From message history (most recent across all sessions)
    candidate_id = chat_request.candidate_id
    if not candidate_id:
        candidate_id = user_context_store.get_current_candidate(user_email)
    if not candidate_id:
        # Look up most recent candidate from message history
        candidate_id = message_store.get_most_recent_candidate_id(user_email)
        if candidate_id:
            # Set as current candidate in user context
            user_context_store.set_current_candidate(user_email, candidate_id)
    
    start_time = time.time()
    
    # Log user message
    system_logger.log_message(
        user_email=user_email,
        user_type=current_user["user_type"],
        message=chat_request.message,
        candidate_id=candidate_id or "",
        session_id=session_id,
        request_id=request_id
    )
    
    # Get existing context if candidate_id provided
    # Note: candidate_id might be extracted from message by coordinator agent
    initial_context = {}
    if candidate_id:
        existing_context = context_store.get_context(candidate_id)
        if existing_context:
            # Only use if candidate is active
            if existing_context.state.value == "active":
                initial_context = existing_context.model_dump()
            else:
                # Candidate is closed, clear from user context
                user_context_store.clear_current_candidate(user_email)
                candidate_id = ""
                initial_context = {}
    
    # Load message history for candidate (last 10 messages)
    message_history = []
    if candidate_id:
        message_history = message_store.get_messages(candidate_id, limit=10, offset=0)
    
    # Capture variables for closure
    captured_candidate_id = candidate_id
    captured_context = initial_context
    captured_message_history = message_history
    
    async def event_generator():
        try:
            # Create initial state
            initial_state: AgentState = {
                "message": chat_request.message,
                "candidate_id": captured_candidate_id or "",  # May be empty, coordinator will extract if needed
                "context": captured_context,
                "research_data": {},
                "recommendation": {},
                "response": "",
                "next_step": "collect",
                "updated_by": user_email,  # Pass user email for context saving
                "user_email": user_email,  # Pass user email for command handling
                "user_type": current_user["user_type"],
                "message_history": captured_message_history,  # Pass message history to coordinator
                "missing_fields": [],
                "extracted_fields": {}
            }
            
            # Run agent workflow with keepalive pings using background task
            final_state = None
            step_messages = {
                "coordinator": "🔍 Analyzing your message and extracting candidate information...",
                "data_collection": "📊 Collecting market data and internal parity information...",
                "research": "🔬 Researching compensation data and generating recommendation...",
                "judge": "⚖️ Validating recommendation quality...",
                "respond": "✍️ Finalizing response..."
            }
            
            # Keepalive mechanism using queue
            ping_interval = 3.0  # seconds
            message_queue = asyncio.Queue()
            workflow_complete = False
            
            async def workflow_runner():
                """Run workflow and put messages in queue."""
                nonlocal final_state, workflow_complete
                try:
                    async for step_output in agent_workflow.astream(initial_state, stream_mode="updates"):
                        final_state = step_output
                        
                        # Stream intermediate updates with descriptive messages
                        node_name = list(step_output.keys())[0] if isinstance(step_output, dict) else "unknown"
                        status_message = step_messages.get(node_name, f"Processing {node_name}...")
                        
                        # Get state from step output to provide more context
                        step_state = None
                        if isinstance(step_output, dict) and len(step_output) > 0:
                            step_state = list(step_output.values())[0]
                        
                        # Extract additional context for status updates
                        status_data = {
                            "type": "processing",
                            "step": node_name,
                            "message": status_message
                        }
                        
                        # Add specific details based on step
                        if step_state and isinstance(step_state, dict):
                            if node_name == "coordinator":
                                # Show if candidate was extracted
                                extracted_id = step_state.get("candidate_id")
                                if extracted_id:
                                    status_data["candidate_id"] = extracted_id
                                    status_data["message"] = f"✅ Extracted candidate ID: {extracted_id}. Analyzing requirements..."
                                # Check if triggering research
                                next_step = step_state.get("next_step")
                                if next_step == "research":
                                    status_data["message"] = "✅ All information collected. Initiating research..."
                            elif node_name == "data_collection":
                                research_data = step_state.get("research_data", {})
                                market_data = research_data.get("market_data", {})
                                internal_parity = research_data.get("internal_parity", {})
                                if market_data.get("available"):
                                    status_data["message"] = "✅ Market data collected. Gathering internal parity data..."
                                else:
                                    status_data["message"] = "⚠️ Market data not found. Checking alternatives..."
                            elif node_name == "research":
                                research_data = step_state.get("research_data", {})
                                recommendation = step_state.get("recommendation", {})
                                if recommendation:
                                    status_data["message"] = "✅ Recommendation generated. Reviewing details..."
                                else:
                                    status_data["message"] = "🔬 Analyzing market data and generating compensation recommendation..."
                            elif node_name == "judge":
                                recommendation = step_state.get("recommendation", {})
                                if recommendation.get("status") == "approved":
                                    status_data["message"] = "✅ Recommendation validated. Preparing final response..."
                                else:
                                    status_data["message"] = "⚖️ Validating recommendation quality and data accuracy..."
                        
                        # Put message in queue
                        await message_queue.put(("message", status_data))
                finally:
                    workflow_complete = True
                    await message_queue.put(("complete", None))
            
            async def ping_sender():
                """Send periodic keepalive pings."""
                while not workflow_complete:
                    await asyncio.sleep(ping_interval)
                    if not workflow_complete:
                        await message_queue.put(("ping", {"type": "keepalive", "timestamp": time.time()}))
            
            # Start both tasks
            workflow_task = asyncio.create_task(workflow_runner())
            ping_task = asyncio.create_task(ping_sender())
            
            # Yield messages from queue
            try:
                while True:
                    msg_type, data = await message_queue.get()
                    
                    if msg_type == "complete":
                        break
                    elif msg_type == "ping":
                        yield {
                            "event": "ping",
                            "data": json.dumps(data)
                        }
                    elif msg_type == "message":
                        yield {
                            "event": "message",
                            "data": json.dumps(data)
                        }
            finally:
                # Cancel ping task if still running
                if not ping_task.done():
                    ping_task.cancel()
                # Wait for workflow to complete
                await workflow_task
            
            # Get final response
            if final_state:
                # Extract state from final output
                if isinstance(final_state, dict) and len(final_state) > 0:
                    last_node_output = list(final_state.values())[0]
                    if isinstance(last_node_output, dict):
                        last_state = last_node_output
                    else:
                        last_state = final_state
                else:
                    last_state = final_state if isinstance(final_state, dict) else {}
                
                # Extract response from state
                coordinator_response = last_state.get("response", "I'm sorry, I couldn't process your request.")
                recommendation = last_state.get("recommendation", {})
                
                # Debug logging
                logger.debug(f"coordinator_response = {coordinator_response[:200] if coordinator_response else 'None'}")
                logger.debug(f"recommendation keys = {recommendation.keys() if isinstance(recommendation, dict) else 'Not a dict'}")
                logger.debug(f"next_step = {last_state.get('next_step')}")
                
                # Use coordinator response directly - coordinator is responsible for all messaging
                response_text = coordinator_response
                logger.debug(f"Using coordinator response directly: {response_text[:200] if response_text else 'None'}")
                
                # Get candidate_id from state (may have been extracted by coordinator)
                final_candidate_id = last_state.get("candidate_id") or candidate_id
                
                # Initialize context variable - will be updated below if candidate exists
                context = {}
                
                # Update user's current candidate if a new one was extracted and is active
                if final_candidate_id:
                    existing_context = context_store.get_context(final_candidate_id)
                    if existing_context and existing_context.state.value == "active":
                        user_context_store.set_current_candidate(user_email, final_candidate_id)
                        # Reload context
                        context = existing_context.model_dump()
                    elif existing_context and existing_context.state.value == "closed":
                        # Candidate is closed, don't set as current
                        final_candidate_id = ""
                        user_context_store.clear_current_candidate(user_email)
                        context = {}
                
                # Update context if candidate_id available (either provided or extracted)
                if final_candidate_id:
                    
                    # Extract structured data from response/state
                    # First, try to get from research_data (when all fields are ready)
                    research_data = last_state.get("research_data", {})
                    context_data = {}
                    if "job_title" in research_data:
                        context_data["job_title"] = research_data["job_title"]
                    if "location" in research_data:
                        context_data["location"] = research_data["location"]
                    if "level" in research_data:
                        context_data["job_level"] = research_data["level"]
                    if "proficiency" in research_data:
                        context_data["interview_feedback"] = research_data["proficiency"]
                        context_data["proficiency"] = research_data["proficiency"]
                    if "job_family" in research_data:
                        context_data["job_family"] = research_data["job_family"]
                    
                    # Also check for extracted_fields from coordinator (partial extraction)
                    extracted_fields = last_state.get("extracted_fields", {})
                    if extracted_fields:
                        if "location" in extracted_fields:
                            context_data["location"] = extracted_fields["location"]
                        if "proficiency" in extracted_fields:
                            context_data["proficiency"] = extracted_fields["proficiency"]
                            context_data["interview_feedback"] = extracted_fields.get("interview_feedback", extracted_fields["proficiency"])
                        if "job_level" in extracted_fields:
                            context_data["job_level"] = extracted_fields["job_level"]
                    
                    # Also use updated context from coordinator if available
                    updated_context = last_state.get("context", {})
                    if updated_context:
                        # Merge updated context, prioritizing research_data and extracted_fields
                        for key in ["location", "job_title", "job_level", "proficiency", "interview_feedback", "job_family"]:
                            if key in updated_context and key not in context_data:
                                context_data[key] = updated_context[key]
                    
                    if context_data:
                        context_store.save_context(final_candidate_id, context_data, current_user["email"])
                
                # Stream final response
                # ALWAYS include candidate_id if we have one, to ensure UI stays in sync
                response_candidate_id = final_candidate_id

                
                # Store recommendation in context (for future features like PDF generation)
                recommendation = last_state.get("recommendation", {})
                if recommendation and final_candidate_id:
                    # Save recommendation data to context
                    rec_data = {}
                    if isinstance(recommendation, dict):
                        rec = recommendation.get("recommendation", {})
                        if rec:
                            rec_data = {
                                "base_salary": rec.get("base_salary"),
                                "base_salary_percentile": rec.get("base_salary_percentile"),
                                "base_salary_percent_of_range": rec.get("base_salary_percent_of_range"),
                                "bonus_percentage": rec.get("bonus_percentage"),
                                "bonus_amount": rec.get("bonus_amount"),
                                "equity_amount": rec.get("equity_amount"),
                                "total_compensation": rec.get("total_compensation"),
                                "market_range": rec.get("market_range"),
                                "internal_parity": rec.get("internal_parity"),
                            }
                            reasoning = rec.get("reasoning", {})
                            if reasoning:
                                # Handle reasoning being a string or dict
                                if isinstance(reasoning, str):
                                    rec_data["reasoning"] = reasoning
                                elif isinstance(reasoning, dict):
                                    rec_data.update({
                                        "market_data_analysis": reasoning.get("market_data_analysis", ""),
                                        "internal_parity_analysis": reasoning.get("internal_parity_analysis", ""),
                                        "job_family_impact": reasoning.get("job_family_impact", ""),
                                        "proficiency_impact": reasoning.get("proficiency_impact", ""),
                                        "level_impact": reasoning.get("level_impact", ""),
                                        "band_placement_reasoning": reasoning.get("band_placement_reasoning", ""),
                                        "equity_allocation_reasoning": reasoning.get("equity_allocation_reasoning", ""),
                                        "bonus_percentage_reasoning": reasoning.get("bonus_percentage_reasoning", ""),
                                        "data_sources_used": reasoning.get("data_sources_used", ""),
                                        "considerations_and_tradeoffs": reasoning.get("considerations_and_tradeoffs", ""),
                                    })
                        if rec_data:
                            context_store.save_context(final_candidate_id, rec_data, current_user["email"])
                
                # Include recommendation data for detailed explanation in sidebar
                recommendation_for_response = None
                if recommendation and isinstance(recommendation, dict) and recommendation.get("status") == "approved":
                    recommendation_for_response = recommendation
                    
                    # Inject history from candidate context
                    if final_candidate_id:
                         ctx = context_store.get_context(final_candidate_id)
                         if ctx and ctx.recommendation_history:
                             # Sort history by timestamp desc (newest first)
                             history_sorted = sorted(ctx.recommendation_history, key=lambda h: h.timestamp, reverse=True)
                             recommendation_for_response["history"] = [h.model_dump() for h in history_sorted]
                
                # Stream the response from coordinator (coordinator is responsible for all messaging)
                print(f"DEBUG: Streaming final response. Candidate: {response_candidate_id}, Has recommendation: {recommendation_for_response is not None}")
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "response",
                        "content": response_text,
                        "response_id": request_id,
                        "candidate_id": response_candidate_id,  # Only include if active
                        "recommendation": recommendation_for_response  # Include for sidebar display
                    })
                }

                
                # Save message to message store (always save - messages are per user)
                print(f"DEBUG: Attempting to save message for user={user_email}, candidate={final_candidate_id}")
                try:
                    print(f"DEBUG: Saving message. Response length: {len(response_text) if response_text else 0}")
                    message_store.save_message(
                        user_email=user_email,
                        message=chat_request.message,
                        response=response_text,
                        session_id=session_id,
                        request_id=request_id,
                        candidate_id=final_candidate_id  # Optional - can be None
                    )
                    print(f"DEBUG: Message saved successfully")
                except Exception as e:
                    print(f"Error saving message: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Log response
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                system_logger.log_response(
                    user_email=current_user["email"],
                    user_type=current_user["user_type"],
                    response=response_text,
                    candidate_id=final_candidate_id,  # Use final candidate_id
                    session_id=session_id,
                    request_id=request_id,
                    response_time_ms=response_time,
                    context_snapshot=context
                )
        except Exception as e:
            import traceback
            error_msg = f"Error processing request: {str(e)}"
            error_traceback = traceback.format_exc()
            print(f"Error in chat stream: {error_msg}")
            print(f"Traceback: {error_traceback}")
            system_logger.log(
                event_type="Error",
                user_email=current_user["email"],
                user_type=current_user["user_type"],
                candidate_id=candidate_id or "",
                request_id=request_id,
                status="Error",
                error_message=error_msg
            )
            yield {
                "event": "error",
                "data": json.dumps({"error": error_msg, "details": error_traceback[:500]})
            }
    
    return EventSourceResponse(event_generator())


@app.post("/api/context/reset")
async def reset_context(reset_request: ContextResetRequest, current_user: dict = Depends(get_current_user)):
    """Reset context for a candidate (requires Comp Team permission)."""
    if current_user["user_type"] != UserType.COMP_TEAM:
        raise HTTPException(status_code=403, detail="Only Comp Team members can reset context")
    
    candidate_id = reset_request.candidate_id
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id is required")
    
    success = context_store.reset_context(candidate_id, current_user["email"])
    
    if success:
        system_logger.log_context_update(
            user_email=current_user["email"],
            user_type=current_user["user_type"],
            candidate_id=candidate_id,
            field="reset",
            old_value="exists",
            new_value="deleted"
        )
        return {"status": "success", "message": f"Context for candidate {candidate_id} has been reset"}
    else:
        return {"status": "not_found", "message": f"No context found for candidate {candidate_id}"}


@app.get("/api/context/{candidate_id}")
async def get_context(candidate_id: str, current_user: dict = Depends(get_current_user)):
    """Get candidate context."""
    context = context_store.get_context(candidate_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"No context found for candidate {candidate_id}")
    
    return {
        "candidate_id": candidate_id,
        "context": context.model_dump(),
        "last_updated": context.updated_at.isoformat()
    }


@app.get("/api/audit/{candidate_id}")
async def get_audit_log(candidate_id: str, current_user: dict = Depends(get_current_user)):
    """Get audit log for a candidate."""
    audit_log = context_store.get_audit_log(candidate_id)
    return audit_log


@app.get("/api/messages")
async def get_messages(
    candidate_id: str = None,
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get messages for current user with optional candidate filter."""
    user_email = current_user["email"]
    messages = message_store.get_messages(user_email, limit=limit, offset=offset, candidate_id=candidate_id)
    total = message_store.get_message_count(user_email, candidate_id=candidate_id)
    
    return {
        "user_email": user_email,
        "candidate_id": candidate_id,
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/messages/all")
async def get_all_messages(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get all messages for current user (full conversation history)."""
    user_email = current_user["email"]
    messages = message_store.get_all_messages(user_email, limit=limit)
    
    return {
        "user_email": user_email,
        "messages": messages,
        "total": len(messages)
    }


@app.get("/api/user/current-candidate")
async def get_current_candidate(current_user: dict = Depends(get_current_user)):
    """Get user's current active candidate."""
    candidate_id = user_context_store.get_current_candidate(current_user["email"])
    
    if candidate_id:
        context = context_store.get_context(candidate_id)
        # Only return if candidate is active
        if context and context.state.value == "active":
            return {
                "candidate_id": candidate_id,
                "context": context.model_dump()
            }
        else:
            # Candidate is closed, clear from user context
            user_context_store.clear_current_candidate(current_user["email"])
            return {"candidate_id": None, "context": None}
    
    return {"candidate_id": None, "context": None}


@app.get("/api/user/candidates")
async def get_user_candidates(
    state: Optional[str] = None,  # "active" or "closed"
    current_user: dict = Depends(get_current_user)
):
    """Get user's candidates (active or closed)."""
    if state == "closed":
        candidates = context_store.get_closed_candidates(current_user["email"])
    else:
        candidates = context_store.get_active_candidates(current_user["email"])
    
    return {
        "candidates": [c.model_dump() for c in candidates]
    }


@app.get("/api/logs")
async def get_logs(
    candidate_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
    user_email: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Query system logs with filters."""
    # Simple implementation - in production, use proper filtering
    # For now, return all logs (implement CSV reading and filtering)
    return {"message": "Log query endpoint - implement CSV filtering"}


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback_request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """Submit user feedback on a response."""
    feedback_id = str(uuid.uuid4())
    
    # Log feedback
    system_logger.log_feedback(
        user_email=current_user["email"],
        user_type=current_user["user_type"],
        response_id=feedback_request.response_id,
        feedback_type=feedback_request.feedback_type.value,
        comment=feedback_request.comment,
        candidate_id=feedback_request.candidate_id
    )
    
    return FeedbackResponse(
        status="success",
        feedback_id=feedback_id
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Compensation Recommendation Assistant API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Application startup - no seeding, candidates are created by users."""
    pass
