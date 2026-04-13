
---

## `08_ONBOARDING_FIELDS_AND_FLOW.md`

```md id="a8k4m2"
# Onboarding Fields and Flow

## Goal
Collect only the information required to:
- identify the user's UK tax/compliance path
- connect any registered company
- determine applicable modules
- enable reminders and deadlines
- avoid overwhelming signup

The onboarding should be a hybrid:
- guided steps
- structured fields
- agent clarification only when needed

## Recommended Flow

### Step 1 — Who is this account for?
Fields:
- acting_as
  - self
  - my_business
  - my_company_and_me
  - accountant_or_bookkeeper_for_clients

Purpose:
- determines base context
- affects later UI and pipeline activation

---

### Step 2 — What type of taxpayer or business are you?
Fields:
- business_type
  - sole_trader
  - limited_company
  - landlord
  - sole_trader_and_landlord
  - partnership
  - accountant_or_bookkeeper
  - not_sure

Purpose:
- determines which major compliance paths apply

---

### Step 3 — Is the company already registered?
Show only if business_type includes limited_company.

Fields:
- company_registration_status
  - already_registered
  - want_to_register
  - registration_in_progress
  - not_sure

If already_registered:
- company_name_or_number
- optional exact company_number

Purpose:
- enables Companies House verification and deadline import

---

### Step 4 — Income type selection
Fields:
- income_types[]
  - self_employment_income
  - rental_property_income
  - limited_company_income
  - employment_income
  - dividends
  - savings_interest
  - capital_gains
  - other

Purpose:
- helps identify Self Assessment and property-related needs

---

### Step 5 — Self Assessment status
Fields:
- self_assessment_registered
  - yes
  - no
  - not_sure

- utr_available
  - yes
  - no
  - not_sure

- government_gateway_access
  - yes
  - no
  - not_sure

Purpose:
- helps assess HMRC setup status

---

### Step 6 — Business/property start dates
Fields:
- business_start_date
- trading_start_date
- property_income_start_date

These should appear conditionally depending on user type.

Purpose:
- important for tax start context
- helps MTD and compliance review

---

### Step 7 — Turnover / income estimate
Fields:
- estimated_annual_self_employment_income
- estimated_annual_property_income
- estimated_12_month_taxable_turnover

Purpose:
- helps assess likely VAT monitoring and MTD-related review

---

### Step 8 — VAT status
Fields:
- vat_status
  - vat_registered
  - not_vat_registered
  - not_sure
  - monitor_threshold

If registered:
- vat_number

Purpose:
- enables VAT tracking or threshold monitoring

---

### Step 9 — Payroll / employees
Fields:
- payroll_status
  - no_employees
  - director_only
  - has_employees
  - not_sure

If payroll may apply:
- first_payday_date
- paye_reference_available
- employee_count

Purpose:
- enables payroll/PAYE review

---

### Step 10 — Limited company trade status
Show if business_type includes limited_company.

Fields:
- company_trade_status
  - actively_trading
  - not_yet_trading
  - dormant
  - not_sure

Purpose:
- affects Corporation Tax / active company review

---

### Step 11 — UK location
Fields:
- uk_nation
  - england
  - scotland
  - wales
  - northern_ireland

Purpose:
- useful for later tax/payroll context

---

### Step 12 — Reminder and contact preferences
Fields:
- preferred_reminder_channel
  - in_app
  - email
  - whatsapp
  - slack

- email
- phone_number
- optional_accountant_email

Purpose:
- enables reminder delivery setup

## Minimum Required Fields by Type

### Sole Trader
Required minimum:
- acting_as
- business_type
- income_types
- self_assessment_registered
- business_start_date or trading_start_date
- preferred_reminder_channel
- email

### Landlord
Required minimum:
- acting_as
- business_type
- income_types
- property_income_start_date
- self_assessment_registered
- preferred_reminder_channel
- email

### Limited Company
Required minimum:
- acting_as
- business_type
- company_registration_status
- if registered: company_name_or_number
- company_trade_status
- preferred_reminder_channel
- email

### Limited Company + Director Personal Taxes
Required minimum:
- limited company fields above
- self_assessment_registered
- income_types
- reminder preferences

## Conditional Logic Rules

### If company_registration_status = already_registered
Then:
- verify company with Companies House
- store company verification result
- preload Companies House deadlines if available

### If business_type includes landlord
Then:
- ask property income start date
- ask property income estimate

### If estimated_12_month_taxable_turnover is high or near threshold
Then:
- enable VAT monitoring or review flag

### If payroll_status indicates employees or director payroll
Then:
- enable payroll review path

### If user selects not_sure for key tax setup fields
Then:
- mark relevant fields as needs_review
- do not force false precision

## Onboarding Summary Screen
At the end of onboarding, show a structured summary:

- profile type
- company verification result
- reminder channel
- active modules
- missing fields
- needs review items

User should confirm summary before final submission.

## Confirmation Statement
Before final save, show:

"I’ve prepared your setup profile based on the information provided. Verified items, user-provided items, and items needing review are tracked separately."

## Storage Expectations
The onboarding flow should store:
- raw answers
- normalized field values
- source classification
- verification status
- timestamp per field
- onboarding completion status