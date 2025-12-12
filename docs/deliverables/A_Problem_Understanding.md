# A. Problem Understanding

## Primary Problem: Time-to-Recommendation Delay

**The Critical Constraint**: The current manual compensation recommendation process often takes **up to 2 days** to generate a single recommendation. This significant delay creates bottlenecks in the hiring process, impacts candidate experience, and reduces the efficiency of the compensation team.

**Impact of 2-Day Delay**:
- Candidates may receive competing offers while waiting for compensation recommendations
- Recruiters cannot move forward with offer negotiations in a timely manner
- Compensation team members are blocked on multiple candidates simultaneously
- Hiring velocity is significantly reduced
- Competitive disadvantage in fast-moving talent markets

**Target Improvement**: Reduce recommendation generation time from **2 days to minutes** through automated data collection, intelligent agent orchestration, and streamlined workflows.

## Problem Statement

The Compensation Recommendation Conversational Assistant addresses the challenge of generating accurate, market-aligned, and internally consistent compensation recommendations for candidates who have successfully cleared interviews. The **primary constraint** is the time-consuming manual process that often takes **up to 2 days** to complete a single recommendation. The current process is also prone to inconsistencies and requires compensation team members to manually cross-reference multiple data sources (market compensation data, internal parity data, job family norms, and equity allocation guidelines).

## Pain Points

1. **Critical Time Delay - 2 Days Per Recommendation**: 
   - Manual data collection and cross-referencing takes 1.5-2 days per candidate
   - Multiple systems must be accessed sequentially, creating bottlenecks
   - Manual calculations and validations require significant time investment
   - This delay is the **primary constraint** affecting hiring velocity and candidate experience
   - Compensation team members are often blocked on multiple candidates simultaneously

2. **Inconsistency**: Different team members may arrive at different recommendations for similar candidates, requiring additional review cycles

3. **Data Access Friction**: Multiple systems and spreadsheets must be accessed separately, each requiring authentication and navigation time

4. **Context Loss**: Candidate information and previous discussions are not systematically captured, leading to repeated information gathering

5. **Limited Traceability**: No clear audit trail of how recommendations were derived, making reviews and approvals time-consuming

6. **Collaboration Challenges**: Recruiters and compensation team members work in silos with limited context sharing, requiring back-and-forth communication that adds days to the process

7. **Error Risk**: Manual calculations and data entry increase the likelihood of errors, requiring corrections that further extend the timeline

## Key Constraints

### Technical Constraints

1. **Zero Hallucination Requirement**: 
   - System must only use exact matches from CSV data sources
   - No approximations, estimations, or AI-generated compensation values
   - All recommendations must be traceable to specific data rows

2. **Data Source Limitations**:
   - MVP uses mock CSV files (CompRanges.csv, EmployeeRoster.csv) instead of real Workday/Greenhouse integrations
   - Exact-match lookups only (no fuzzy matching or fallbacks)
   - Percentile calculations performed for band placement within market ranges

3. **Context Retention**:
   - Candidate context persists for 60 days maximum
   - Auto-expiry after retention period
   - Shared context across all users for the same Candidate ID

4. **MVP Scope Limitations**:
   - No real integrations with Workday or Greenhouse
   - Hardcoded user credentials (no full RBAC)
   - No offer letter generation
   - No analytics dashboards
   - No policy-driven compensation modeling

### Business Constraints

1. **Primary Time Constraint - 2-Day Recommendation Delay**: 
   - Current process takes up to 2 days per recommendation
   - This is the **most critical business constraint** driving the need for automation
   - System must reduce this to minutes to be considered successful
   - Time savings directly impact hiring velocity and competitive positioning

2. **User Types**: Two distinct user types (Compensation Team and Recruitment Team) with different permission levels

3. **Permission Rules**: Field-level permissions prevent recruiters from overriding certain compensation-related fields

4. **Audit Requirements**: All context modifications must be logged with user, timestamp, and field changes

5. **Feedback Mechanism**: Simple feedback system (thumbs down / report error) for evaluation purposes only

## Key Assumptions

1. **Data Quality**: 
   - CSV data files (CompRanges.csv, EmployeeRoster.csv) are accurate and up-to-date
   - Market compensation data reflects current market conditions
   - Internal roster data is maintained and current

2. **User Behavior**:
   - Users will follow the conversational flow to provide required information
   - Users have access to candidate interview feedback before initiating compensation discussions
   - Users understand job levels (P1-P5) and job family classifications

3. **System Reliability**:
   - CSV files are accessible and not corrupted
   - Network connectivity supports Server-Sent Events (SSE) streaming
   - LLM API providers (OpenAI, Gemini) are available and responsive

4. **Collaboration Model**:
   - Recruiters and compensation team members will collaborate on the same candidate context
   - Users understand the shared context model and permission boundaries
   - Context handoffs between teams are seamless

## Tradeoffs

### 1. Exact-Match Only vs. Coverage

**Decision**: Exact-match lookups only, no approximations

**Tradeoff**: 
- **Pros**: Ensures zero hallucination, guarantees data accuracy, provides clear audit trail
- **Cons**: May result in "no data found" scenarios for valid job title/location combinations not in CSV files, requires comprehensive data coverage

**Rationale**: Accuracy and trust are paramount for compensation recommendations. Better to return "no data found" than to provide incorrect recommendations based on approximations.

### 2. Mock Data vs. Real Integrations (MVP)

**Decision**: Use mock CSV files to simulate Workday/Greenhouse APIs

**Tradeoff**:
- **Pros**: Faster MVP delivery, no dependency on external systems, easier testing and development
- **Cons**: Not production-ready, requires manual data updates, doesn't reflect real-time system state

**Rationale**: MVP focus is on demonstrating the conversational workflow and agent architecture. Real integrations can be added in V2.

### 3. Simple Feedback vs. Detailed Ratings

**Decision**: Thumbs down / report error only (no thumbs up)

**Tradeoff**:
- **Pros**: Reduces user friction, focuses on identifying problems, simpler UX, better signal-to-noise ratio
- **Cons**: No explicit positive feedback, assumes implicit acceptance of non-flagged responses

**Rationale**: MVP approach prioritizes identifying issues over collecting positive feedback. Implicit positive feedback (lack of negative feedback) is sufficient for evaluation.

### 4. Shared Context vs. User-Specific Context

**Decision**: Shared candidate context across all users for the same Candidate ID

**Tradeoff**:
- **Pros**: Matches real-world workflow, enables seamless handoffs, reduces data duplication, ensures consistency
- **Cons**: Requires careful permission management, needs comprehensive audit logging, potential for conflicts if multiple users edit simultaneously

**Rationale**: Real-world compensation workflows involve collaboration between recruiters and compensation team. Shared context better reflects this reality.

### 5. 60-Day Retention vs. Permanent Storage

**Decision**: 60-day context retention with auto-expiry

**Tradeoff**:
- **Pros**: Balances utility with storage costs, aligns with typical candidate lifecycle, reduces data accumulation
- **Cons**: May lose context for long-running processes, requires users to restart conversations after expiry

**Rationale**: Most compensation discussions conclude within 60 days. Longer retention would require more storage and may not provide significant value.

### 6. CSV-Based Logging vs. Database Logging

**Decision**: Log all events to CSV files (system_logs.csv)

**Tradeoff**:
- **Pros**: Simple implementation, easy to export and analyze, no database dependencies
- **Cons**: Less efficient for large-scale queries, limited concurrent write performance, manual analysis required

**Rationale**: MVP approach prioritizes simplicity and observability. Database-backed logging can be added in V2 if needed.

## Success Criteria

The problem is successfully addressed when:

1. **Efficiency - Primary Goal**: Compensation recommendations are generated in **minutes rather than 2 days**
   - Target: Complete recommendation generation in 5-10 minutes from start to finish
   - Reduction: **95%+ time reduction** (from 2 days to minutes)
   - Impact: Compensation team can handle 10-20x more candidates with same resources
   - Candidate experience: Recommendations available same-day, enabling faster offer processes

2. **Accuracy**: All recommendations are based on exact data matches with zero hallucination

3. **Consistency**: Similar candidates receive similar recommendations regardless of which team member creates them

4. **Traceability**: Every recommendation includes clear reasoning and can be traced back to source data

5. **Collaboration**: Recruiters and compensation team members seamlessly collaborate on candidate context, eliminating handoff delays

6. **Trust**: Users trust the system's recommendations because they understand the data sources and reasoning

7. **Observability**: All interactions are logged and can be analyzed for system improvement

**Key Metric**: Time-to-recommendation reduced from **2 days to under 10 minutes** - representing a **99%+ improvement** in process efficiency.

