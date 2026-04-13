# Admin Pipeline Monitor Spec

## Purpose
The Admin Pipeline Monitor is an internal-only control panel that shows how onboarding, routing, verification, and downstream pipeline activation are working for each user.

This page is not for end users.
It exists so admin can understand:
- what the system collected
- what was verified
- what is missing
- which pipelines are active
- why those pipelines were activated
- where onboarding is blocked or uncertain
- how agents handed work to each other

## Visibility Rule
This page must be visible only to admin users.

For v1, simple admin gating is acceptable.
Examples:
- hardcoded admin toggle
- allowlist email
- environment-based admin mode

But the code structure should allow real RBAC later.

## Core Goals
- make onboarding/routing transparent
- make agent-to-agent handoffs inspectable
- make data quality issues easy to spot
- make pipeline activation decisions auditable
- help debug hallucination, missing data, weak verification, and wrong routing

## Page Name Options
- Pipeline Monitor
- Onboarding & Pipeline Monitor
- Internal Routing Console
- Admin Control Room

Recommended:
**Onboarding & Pipeline Monitor**

## Main Layout

### Section 1 — User Selector
Admin should be able to:
- search by user id
- search by email
- search by company number
- search by company name

Display:
- selected user
- onboarding status
- last updated timestamp

---

### Section 2 — Profile Overview
Show:
- user id
- email
- acting_as
- business_type
- onboarding status
- onboarding stage
- completion percent
- preferred reminder channel
- created_at
- updated_at

Purpose:
- quick understanding of current profile state

---

### Section 3 — Company Verification Panel
Show:
- raw company input from onboarding
- matched company name
- matched company number
- match status
- companies_house_verified yes/no
- last verification attempt time
- company profile snapshot if available

Possible states:
- not_attempted
- strong_match
- ambiguous_match
- weak_match
- no_verified_match

Purpose:
- quickly diagnose bad company linkage

---

### Section 4 — Onboarding Field Matrix
Display as a table.

Columns:
- field_name
- value
- source_type
- verification_status
- required
- confidence
- last_updated_by
- updated_at

Rows should include all onboarding fields captured so far.

This is one of the most important admin views.
It should make it obvious which fields are:
- verified
- user_provided
- inferred
- missing
- needs_review

Purpose:
- debug onboarding quality
- understand why routing produced its result

---

### Section 5 — Review Flags
Display unresolved and resolved flags.

Columns:
- severity
- flag_type
- message
- related_field
- related_pipeline
- resolved
- resolved_by
- resolved_at
- created_at

Severity colors:
- low = neutral
- medium = yellow
- high = orange
- critical = red

Admin actions for v1:
- mark flag resolved
- optionally add note

Purpose:
- highlight onboarding and routing issues needing intervention

---

### Section 6 — Pipeline Status Board
Display one card or row per pipeline:

Pipelines:
- companies_house
- company_formation
- self_assessment
- property_income
- vat
- payroll
- mtd_income_tax
- reminders

For each pipeline show:
- enabled yes/no
- status
- activation_source
- reason_text
- last updated
- metadata summary

Allowed statuses:
- active
- pending_verification
- monitor
- review
- not_applicable
- setup_incomplete
- blocked_missing_data

Purpose:
- show exactly which workflows the user is entering

---

### Section 7 — Agent Handoff / Responsibility View
Show how agents are currently involved in this user journey.

Display:
- onboarding_agent status
- supervisor_agent status
- compliance_agent relevance
- bookkeeping_agent relevance
- intake_agent relevance

For each:
- role
- currently active yes/no
- reason
- last action/event if available

Purpose:
- make multi-agent system understandable to admin

---

### Section 8 — Event Timeline
Display onboarding and routing events in reverse chronological order.

Possible event types:
- onboarding_started
- field_captured
- field_updated
- company_verification_attempted
- company_verified
- company_verification_failed
- routing_evaluated
- pipeline_activated
- pipeline_deactivated
- review_flag_added
- onboarding_completed
- admin_override

Columns:
- timestamp
- event_type
- actor_type
- actor_name
- short summary

Optional:
- expand row to view payload JSON

Purpose:
- provide audit trail

---

### Section 9 — Reminder Setup Readiness
Show:
- preferred reminder channel
- contact details present/missing
- reminders pipeline status
- whether delivery is:
  - ready
  - setup_incomplete
  - stub_only
  - disabled

Purpose:
- explain why reminder functionality is or is not active

---

## Admin Actions

### v1 Allowed Actions
- rerun onboarding routing evaluation
- refresh company verification
- mark review flag resolved
- inspect event payloads
- inspect pipeline reasons

### v1 Not Required
- direct manual editing of all onboarding fields
- full override UI for every pipeline
- complete audit export
- full workflow replay

These can come later.

## Backend/Data Requirements
The page should read from:
- onboarding_profiles
- onboarding_fields
- onboarding_company_links if implemented
- onboarding_review_flags
- pipeline_statuses
- onboarding_events

Optional secondary reads:
- reminders
- companies
- tool_call_logs
- conversations

## UX Priorities
This page should prioritize:
- clarity
- debug value
- traceability
- density over decoration

It does not need to be beautiful first.
It needs to make wrong routing and missing data obvious.

## Security Rule
This page must never be available to normal users.

Even in v1, there should be a clear separation between:
- user onboarding UI
- admin pipeline monitor UI

## Success Criteria
This page is successful if an admin can answer:
- what do we know about this user?
- what is verified?
- what is missing?
- why is a pipeline active?
- why is a pipeline blocked?
- did company verification succeed?
- what does the onboarding agent think?
- what should happen next?