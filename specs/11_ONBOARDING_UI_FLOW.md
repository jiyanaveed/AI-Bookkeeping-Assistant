# Onboarding UI Flow

## Goal
Design a guided onboarding experience that is:
- easy for non-experts
- structured enough for accurate data collection
- safe against hallucination
- directly usable by downstream agents and admin tools

The onboarding should be a hybrid of:
- guided form steps
- controlled chat prompts
- verification checkpoints
- summary confirmation

## Core UX Rules
- do not ask everything at once
- ask only relevant questions based on prior answers
- keep one main goal per screen
- use selects/radios/date pickers where possible
- use agent chat only for clarification and uncertainty resolution
- always show progress

## Recommended User Flow

### Screen 1 — Welcome / Setup Start
Purpose:
- explain that setup is used to identify deadlines, tax-related workflows, and reminder setup

Show:
- short welcome
- estimated time: 2 to 4 minutes
- CTA: Start setup

---

### Screen 2 — Who is this account for?
Fields:
- acting_as

Options:
- just me
- my business
- my company and me
- I manage clients

UI:
- cards or radio buttons

Agent behavior:
- no freeform chat unless user selects not sure

---

### Screen 3 — What best describes you?
Fields:
- business_type

Options:
- sole trader
- limited company
- landlord
- sole trader + landlord
- partnership
- accountant/bookkeeper
- not sure

UI:
- single-select cards

Agent behavior:
- if not sure, agent asks a short clarification question

---

### Screen 4 — Company registration step
Conditional:
Show only if limited company is involved.

Fields:
- company_registration_status

Options:
- already registered
- want to register
- registration in progress
- not sure

If already registered:
- input company name or company number
- button: Verify company

Behavior:
- Onboarding Agent attempts Companies House match
- UI shows:
  - strong verified match
  - ambiguous result
  - weak result
  - no verified match

Admin significance:
- this step becomes the trigger for Companies House pipeline eligibility

---

### Screen 5 — Income types
Fields:
- income_types[]

Options:
- self-employment
- rental property
- company income
- employment
- dividends
- savings/interest
- capital gains
- other

UI:
- multi-select chips or checkbox cards

Agent behavior:
- use choices to decide which later questions matter

---

### Screen 6 — Tax registration status
Fields:
- self_assessment_registered
- utr_available
- government_gateway_access

Conditional:
Show only if likely relevant from prior steps.

UI:
- yes/no/not sure selectors

Agent behavior:
- if several answers are not sure, mark review-needed instead of forcing more detail

---

### Screen 7 — Business/property dates
Conditional fields:
- business_start_date
- trading_start_date
- property_income_start_date

UI:
- date pickers
- clear “not sure” option where appropriate

Agent behavior:
- do not invent dates
- mark missing or review-needed where appropriate

---

### Screen 8 — VAT and turnover
Fields:
- vat_status
- vat_number if relevant
- estimated_12_month_taxable_turnover
- estimated_annual_self_employment_income
- estimated_annual_property_income

UI:
- yes/no/not sure
- currency input

Behavior:
- app can show soft note:
  - "We use this to assess VAT monitoring and MTD review needs."

---

### Screen 9 — Payroll / employees
Fields:
- payroll_status
- first_payday_date
- paye_reference_available
- employee_count

Conditional:
Only show if business profile suggests it may matter.

---

### Screen 10 — Reminder preferences
Fields:
- preferred_reminder_channel
- email
- phone_number
- optional_accountant_email

Options:
- in-app
- email
- WhatsApp
- Slack

UI:
- select primary channel
- contact field validation

Note:
Even if WhatsApp/Slack delivery is not yet live, store the preference for future use.

---

### Screen 11 — Setup Summary
Show:
- business type
- company verification result
- reminder preference
- active pipelines
- review-needed items
- missing items
- verified vs user-provided items summary

Actions:
- Confirm and save
- Go back and edit

This is the last step before onboarding is committed as complete/complete_with_review_flags.

---

## Admin-only Pipeline Visibility Page

### Purpose
Create one UI page visible only to admin users that shows how onboarding and routing are working internally.

### Page Name
Pipeline Monitor
or
Onboarding & Pipeline Debug

### What it should show

#### Section 1 — User overview
- user id
- user email
- onboarding status
- business type
- acting_as
- last updated

#### Section 2 — Onboarding completion
- completion percent
- current stage
- complete / review / blocked state

#### Section 3 — Field matrix
A table showing:
- field name
- value
- source type
- verification status
- required?
- updated at

This is extremely important for debugging bad onboarding and pipeline activation.

#### Section 4 — Company verification
- raw company input
- matched company
- company number
- match status
- verified yes/no

#### Section 5 — Pipeline status board
Cards or table for:
- companies_house
- company_formation
- self_assessment
- property_income
- vat
- payroll
- mtd_income_tax
- reminders

Each should show:
- enabled yes/no
- current status
- activation source
- reason text

#### Section 6 — Review flags
- severity
- message
- related field
- related pipeline
- resolved/unresolved

#### Section 7 — Event timeline
- onboarding started
- field updates
- company verification attempt
- routing evaluation
- pipeline activation
- admin override

This page should make it obvious how the system reached its current state.

### Admin actions
Optional for v1:
- mark review flag resolved
- rerun routing
- refresh company verification
- force pipeline reevaluation

### Access rule
This page must only be visible to admin users.

No normal user should see:
- raw routing reasons
- verification statuses for all fields
- internal event timeline
- pipeline debug state

## v1 UI recommendation
For v1:
- build user onboarding flow first
- build one simple admin pipeline page second
- keep the page functional, not pretty-first
- prioritize clarity and traceability over polish