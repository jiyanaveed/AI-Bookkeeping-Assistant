# Onboarding Cursor Prompt

Read and use these files as the source of truth before making changes:

- specs/07_ONBOARDING_AGENT_SPEC.md
- specs/08_ONBOARDING_FIELDS_AND_FLOW.md
- specs/09_PIPELINE_ROUTING_RULES.md
- specs/10_ONBOARDING_DATA_MODEL.md
- specs/11_ONBOARDING_UI_FLOW.md

Also continue respecting the previously created project specs and existing backend architecture.

## Objective
Add an onboarding system to the existing UK AI Accountant Agent project.

This onboarding system must:
- collect accurate setup data for UK tax/compliance context
- use a dedicated Onboarding Agent
- store onboarding data in structured tables
- classify fields by source/verification state
- activate the correct downstream pipelines
- provide an admin-only page showing how the pipeline routing works internally

## Critical rules
- do not rebuild the existing backend architecture
- do not replace the current supervisor/compliance setup
- integrate onboarding as a new capability
- keep current chat/reminder flow working
- keep backend as the source of truth
- do not hallucinate onboarding or routing data
- do not silently overwrite verified facts

## What to implement

### 1. Backend data model
Add onboarding-related tables:
- onboarding_profiles
- onboarding_fields
- onboarding_review_flags
- pipeline_statuses
- onboarding_events
- optionally onboarding_company_links if useful in this phase

Use the spec definitions as the reference.

### 2. Onboarding Agent
Add a dedicated Onboarding Agent with responsibilities:
- collect profile data
- validate and verify where possible
- mark values as verified / user_provided / inferred / missing / needs_review
- detect missing critical fields
- produce a structured onboarding result
- activate routing logic
- hand off clean state to the Supervisor Agent

Do not make this agent overly chatty.
It should act like an accountant intake specialist.

### 3. Onboarding service logic
Implement service logic for:
- saving onboarding field values
- recalculating onboarding completion
- generating review flags
- evaluating pipeline routing based on structured rules
- saving pipeline status records
- writing onboarding events/audit trail

### 4. User onboarding UI
Add a user-facing onboarding flow based on the spec:
- guided steps
- structured fields
- conditional questions
- summary confirmation step

For v1, this can be a simple internal web UI consistent with the existing internal frontend.

### 5. Admin-only pipeline monitor page
Add one admin-only UI page that shows how the onboarding/pipeline system is working.

This page must show:
- user overview
- onboarding completion state
- field matrix
- company verification result
- pipeline status board
- review flags
- onboarding event timeline

Access control:
- visible only to admin users
- hidden from normal users

For now, simple admin gating is acceptable if full auth is not yet implemented, but structure the code so real role-based auth can be added later.

### 6. Routing logic
Implement routing rules from the pipeline spec for:
- Companies House
- company formation
- Self Assessment
- property income
- VAT
- payroll/PAYE
- MTD Income Tax monitoring
- reminders

Store routing outputs in pipeline_statuses.

### 7. Company verification in onboarding
If the user enters an existing company:
- verify through current Companies House integration
- store verification result
- set company match status clearly
- avoid strong claims if only weak/ambiguous matches are found

### 8. Keep implementation practical
For v1:
- focus on reliable structured onboarding and pipeline visibility
- do not overengineer
- do not build every future feature now
- keep UI functional and easy to test
- keep SQLite compatibility

## Deliverables
After implementing, provide:
1. files created/changed
2. schema changes
3. routes/endpoints added
4. onboarding UI flow summary
5. admin-only pipeline page summary
6. how to test onboarding locally
7. what is fully working vs stubbed