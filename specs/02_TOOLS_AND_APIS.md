# Tools and API Contracts

## Source of Truth Rule
The model is never the source of truth.
Tools and verified user-provided data are the source of truth.

## Tool Groups

### A. Companies House Tools

#### 1. search_company_by_name
Purpose:
- search UK registered companies by company name or partial name

Inputs:
- query: string

Outputs:
- candidates: array of
  - company_name
  - company_number
  - company_status

Rules:
- use when user provides a company name but not number
- if multiple likely matches exist, ask user to choose
- never pick randomly

Read-only:
- yes

#### 2. get_company_profile
Purpose:
- fetch verified company profile data

Inputs:
- company_number: string

Outputs:
- company_name
- company_number
- company_status
- incorporation_date
- registered_office_address
- sic_codes
- accounts_due_date if available
- confirmation_statement_due_date if available
- last_synced_at

Read-only:
- yes

#### 3. get_company_deadlines
Purpose:
- retrieve normalized important company deadlines

Inputs:
- company_number: string

Outputs:
- accounts_due_date
- confirmation_statement_due_date
- overdue_flags
- upcoming_deadlines[]
- source_label

Rules:
- use for all deadline questions
- never answer deadline questions from memory

Read-only:
- yes

#### 4. get_company_filing_history
Purpose:
- retrieve filing history

Inputs:
- company_number: string

Outputs:
- filings[]
  - date
  - type
  - description

Read-only:
- yes

---

### B. Reminder Tools

#### 5. create_reminder
Purpose:
- create a reminder for a deadline or task

Inputs:
- entity_type
- entity_id
- reminder_type
- reminder_date
- channel

Outputs:
- reminder_status
- reminder_id

Rules:
- must require explicit user confirmation before execution
- never auto-create reminder

Read-only:
- no

Confirmation required:
- yes

#### 6. list_upcoming_deadlines
Purpose:
- show tracked deadlines/reminders for the current user

Inputs:
- user_id or workspace context

Outputs:
- upcoming_deadlines[]

Read-only:
- yes

---

### C. Bookkeeping Tools

#### 7. get_user_transactions
Purpose:
- return stored transactions for a date range

Inputs:
- user_id
- date_range

Outputs:
- transactions[]
- categorized_count
- uncategorized_count

Read-only:
- yes

#### 8. categorize_transactions
Purpose:
- propose categories for transactions

Inputs:
- transaction_ids or transaction batch

Outputs:
- category suggestions
- confidence scores

Rules:
- suggestions are not final truth until saved
- low-confidence cases should be flagged

Read-only:
- no

Confirmation required:
- yes if saving changes

#### 9. get_monthly_summary
Purpose:
- compute monthly totals

Inputs:
- user_id
- month

Outputs:
- income
- expenses
- net
- top_categories
- anomalies if available

Read-only:
- yes

---

### D. Receipt / Document Tools

#### 10. parse_receipt_document
Purpose:
- extract structured fields from receipt or invoice image/PDF

Inputs:
- file reference

Outputs:
- merchant
- date
- total
- tax
- currency
- line_items if available
- confidence

Rules:
- extracted values must be marked with confidence
- if parse quality is low, ask user to verify

Read-only:
- yes

## Failure Handling Rules

If a tool returns no data:
- say what was searched
- say no verified result was found
- ask for better identifier if needed

If a tool returns ambiguous results:
- show top candidates
- ask user to confirm the correct one

If a tool errors:
- tell the user the lookup failed
- do not guess
- ask whether to retry