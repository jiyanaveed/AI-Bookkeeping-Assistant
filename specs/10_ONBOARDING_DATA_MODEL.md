# Onboarding Data Model

## Goal
Store onboarding data in a structured, auditable, and pipeline-safe way.

The onboarding system must not rely only on chat history.
It must persist:
- normalized profile data
- field-level source classification
- verification status
- routing outcomes
- completion status
- review flags
- admin-visible audit context

## Design Principles
- every important field must be stored separately
- verified facts must be distinguishable from user-entered facts
- uncertain values must not be stored as verified
- routing decisions must be queryable
- future agents must be able to consume onboarding state safely

## Tables

### 1. onboarding_profiles
Represents the current onboarding state for one user/account.

Fields:
- id
- user_id
- status
- acting_as
- business_type
- onboarding_stage
- completion_percent
- summary_json
- created_at
- updated_at

### Field descriptions
- status:
  - not_started
  - in_progress
  - complete
  - complete_with_review_flags
  - blocked_missing_critical_data

- onboarding_stage:
  - account_type
  - registration
  - tax_status
  - identifiers
  - dates
  - reminder_preferences
  - summary
  - completed

- summary_json:
  - cached onboarding summary for fast display

---

### 2. onboarding_fields
Stores field-level captured values and metadata.

Fields:
- id
- onboarding_profile_id
- field_name
- field_value_text nullable
- field_value_json nullable
- source_type
- verification_status
- confidence nullable
- is_required
- notes nullable
- captured_by_agent
- last_updated_by
- created_at
- updated_at

### Allowed values

#### source_type
- verified
- user_provided
- inferred
- missing
- needs_review

#### verification_status
- verified
- unverified
- inferred
- conflicting
- missing
- review_required

### Examples
- field_name: company_number
- field_value_text: 00445790
- source_type: verified
- verification_status: verified

or

- field_name: self_assessment_registered
- field_value_text: not_sure
- source_type: user_provided
- verification_status: review_required

---

### 3. onboarding_company_links
Tracks company verification and linkage during onboarding.

Fields:
- id
- onboarding_profile_id
- company_name_input
- company_number_input nullable
- matched_company_name nullable
- matched_company_number nullable
- company_match_status
- companies_house_verified
- profile_snapshot_json nullable
- created_at
- updated_at

### company_match_status
- not_attempted
- strong_match
- ambiguous_match
- weak_match
- no_verified_match

Purpose:
- separates raw user input from verified company linkage

---

### 4. onboarding_review_flags
Stores issues requiring user or admin attention.

Fields:
- id
- onboarding_profile_id
- flag_type
- severity
- message
- field_name nullable
- pipeline_name nullable
- resolved
- resolved_by nullable
- resolved_at nullable
- created_at

### flag_type examples
- missing_required_field
- ambiguous_company_match
- possible_vat_review
- self_assessment_uncertain
- payroll_review_needed
- reminder_setup_incomplete

### severity
- low
- medium
- high
- critical

---

### 5. pipeline_statuses
Stores downstream pipeline activation state.

Fields:
- id
- onboarding_profile_id
- pipeline_name
- enabled
- status
- activation_source
- reason_text
- metadata_json nullable
- created_at
- updated_at

### pipeline_name values
- companies_house
- company_formation
- self_assessment
- property_income
- vat
- payroll
- mtd_income_tax
- reminders

### status values
- active
- pending_verification
- monitor
- review
- not_applicable
- setup_incomplete
- blocked_missing_data

### activation_source values
- verified_rule
- inferred_rule
- manual_admin_override
- user_update

---

### 6. onboarding_events
Audit log for onboarding and routing changes.

Fields:
- id
- onboarding_profile_id
- event_type
- actor_type
- actor_name
- event_payload_json
- created_at

### actor_type
- onboarding_agent
- supervisor_agent
- admin
- system
- user

### event_type examples
- onboarding_started
- field_captured
- field_updated
- company_verification_attempted
- company_verified
- routing_evaluated
- pipeline_activated
- pipeline_deactivated
- onboarding_completed
- admin_override

Purpose:
- lets admin inspect how the profile reached its current state

---

## Recommended Initial Required Fields
These should be represented in onboarding_fields.

Core fields:
- acting_as
- business_type
- company_registration_status
- company_name_or_number
- income_types
- self_assessment_registered
- utr_available
- government_gateway_access
- business_start_date
- trading_start_date
- property_income_start_date
- estimated_annual_self_employment_income
- estimated_annual_property_income
- estimated_12_month_taxable_turnover
- vat_status
- vat_number
- payroll_status
- first_payday_date
- paye_reference_available
- employee_count
- company_trade_status
- uk_nation
- preferred_reminder_channel
- email
- phone_number
- optional_accountant_email

## Admin Query Use Cases
This model should support admin questions like:
- why was Companies House pipeline activated?
- which onboarding fields are still missing?
- which values were verified vs user-provided?
- which users are blocked on critical onboarding data?
- which users have incomplete reminder setup?
- which company matches are ambiguous?
- what changed when routing was recalculated?

## v1 Implementation Guidance
For v1:
- add onboarding_profiles
- add onboarding_fields
- add onboarding_review_flags
- add pipeline_statuses
- add onboarding_events

onboarding_company_links can also be included in v1 if the company verification flow is added immediately.