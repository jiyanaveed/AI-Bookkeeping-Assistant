# Pipeline Routing Rules

## Purpose
These rules define how onboarding results activate the correct downstream product pipelines.

The system must route based on structured onboarding data, not vague chat assumptions.

## Core Principle
Pipelines should only be activated when:
- enough data exists, or
- provisional routing is clearly marked as inferred or needs_review

## Main Pipelines

### 1. Companies House Pipeline
Enable when:
- business_type includes limited_company
and
- company_registration_status = already_registered
and
- company is verified or strongly matched

Responsibilities:
- company profile sync
- filing history retrieval
- accounts due tracking
- confirmation statement due tracking
- reminder generation

If company is not yet verified:
- do not fully activate
- mark as pending_company_verification

---

### 2. Company Formation Pipeline
Enable when:
- business_type includes limited_company
and
- company_registration_status = want_to_register or registration_in_progress

Responsibilities:
- proposed company intake
- formation readiness tracking
- post-registration follow-up
- move user into Companies House pipeline later

---

### 3. Self Assessment Pipeline
Enable when:
- income_types include self_employment_income, rental_property_income, dividends, or other likely SA-relevant income
or
- user explicitly says they are registered for Self Assessment

Responsibilities:
- Self Assessment readiness
- missing registration flags
- UTR tracking
- personal tax reminders later

If uncertain:
- mark self_assessment as needs_review

---

### 4. Property Income Pipeline
Enable when:
- income_types include rental_property_income
or
- business_type includes landlord

Responsibilities:
- property-income-related tracking
- property start date capture
- Self Assessment/property reminder support
- possible MTD review path

---

### 5. VAT Pipeline
Enable when:
- vat_status = vat_registered
or
- turnover estimate implies VAT monitoring should start

Responsibilities:
- VAT registration tracking
- VAT number capture
- VAT threshold monitoring
- VAT reminders later

If turnover is incomplete or uncertain:
- mark vat_pipeline as monitor_or_review

---

### 6. Payroll / PAYE Pipeline
Enable when:
- payroll_status = has_employees
or
- payroll_status = director_only
or
- first_payday_date is present
or
- PAYE reference exists

Responsibilities:
- payroll/PAYE review
- payroll reminders later
- onboarding completeness checks

If uncertain:
- mark as payroll_review_needed

---

### 7. MTD Income Tax Monitoring Pipeline
Enable when:
- self-employment income or property income exists
and/or
- the user may fall within MTD Income Tax scope

Responsibilities:
- monitor MTD applicability
- remind user of likely MTD relevance
- track whether additional review is needed

Note:
This pipeline may begin as inferred or review-only if income data is incomplete.

---

### 8. Reminder Delivery Pipeline
Enable when:
- preferred_reminder_channel is present
and
- at least one valid contact method is available for that channel

Responsibilities:
- in-app reminder delivery
- email reminder routing
- later WhatsApp/Slack routing

If reminder channel is chosen but required contact details are missing:
- mark reminder_setup_incomplete

## Routing Output Contract
After onboarding, the system should produce a routing object like:

```json
{
  "pipelines": {
    "companies_house": {
      "enabled": true,
      "status": "active"
    },
    "company_formation": {
      "enabled": false,
      "status": "not_applicable"
    },
    "self_assessment": {
      "enabled": true,
      "status": "needs_review"
    },
    "property_income": {
      "enabled": false,
      "status": "not_applicable"
    },
    "vat": {
      "enabled": true,
      "status": "monitor"
    },
    "payroll": {
      "enabled": false,
      "status": "not_applicable"
    },
    "mtd_income_tax": {
      "enabled": true,
      "status": "review"
    },
    "reminders": {
      "enabled": true,
      "status": "setup_complete"
    }
  }
}
Status Vocabulary

Each pipeline should have a status such as:

active
pending_verification
monitor
review
not_applicable
setup_incomplete
blocked_missing_data
Routing Priorities
Priority 1

Verify and activate the most concrete obligations first:

Companies House
reminders
VAT registration if explicit
payroll if explicit
Priority 2

Activate review paths for uncertain obligations:

Self Assessment
MTD
VAT monitoring
Priority 3

Defer advanced flows until more data exists:

bookkeeping intelligence
receipt reconciliation
anomaly detection
accountant collaboration mode
Rules for Downstream Agents
Compliance Agent may read:
verified company data
active compliance pipelines
reminder preferences
Bookkeeping Agent may read:
business type
tax modules
onboarding profile
reminder preferences if needed
Intake Agent may read:
file/document context
business type
active modules for routing
Supervisor Agent may:
read all onboarding results
route based on active pipelines
request missing data collection if onboarding is incomplete
Updating Routing Later

Routing is not frozen forever.

The system may update routing when:

company gets verified later
VAT registration changes
payroll begins
property income is added
user updates profile
accountant reviews the account

But all updates must:

be logged
preserve source classification
avoid silently overwriting verified facts