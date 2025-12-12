Problem Definition & Strategy Summary
1. Primary Problem: The "2-Day Delay"
The current manual process for compensation recommendations takes up to 2 days per candidate. This creates a critical bottleneck that reduces hiring velocity, leaves candidates waiting (risking competing offers), and blocks the compensation team.

Target: Reduce recommendation time from 2 days to minutes.

2. Key Pain Points
Critical Time Delay: Manual data collection and cross-referencing across multiple systems causes the 2-day lag.

Operational Friction: Users face data access friction, lack of audit trails, and collaboration silos between Recruiters and Comp Teams.

Risk: High potential for human error and inconsistency between different team members.

3. Critical Constraints
Technical Constraints

Zero Hallucination: System must use exact matches only from CSV sources. No AI estimations or approximations allowed.

MVP Limitations: Uses mock CSV files (CompRanges.csv, EmployeeRoster.csv) rather than real Workday/Greenhouse integrations.

Context: Shared candidate context persists for 60 days before auto-expiry.

Business Constraints

Permissions: Distinct roles for "Compensation Team" vs. "Recruitment Team" with field-level restrictions.

Auditing: All changes to context must be logged for traceability.

4. Strategic Tradeoffs
Accuracy vs. Coverage: Chosen Exact-Match Only.

Rationale: Better to return "no data found" than an incorrect or hallucinated salary figure.

Speed vs. Integration: Chosen Mock Data (CSVs).

Rationale: Prioritizes fast delivery of the conversational workflow over complex API integrations for the MVP.

Collaboration vs. Isolation: Chosen Shared Context.

Rationale: Recruiters and Comp teams view the same data to eliminate handoff delays, despite the complexity of managing permissions.

5. Success Criteria
Efficiency (Key Metric): Time-to-recommendation reduced from 2 days to <10 minutes (95%+ reduction).

Accuracy: 100% of recommendations are traceable to specific data rows with zero hallucination.

Trust: Full audit trails available for every recommendation.