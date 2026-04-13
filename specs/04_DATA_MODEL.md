# Data Model — Initial Version

## users
- id
- full_name
- email
- phone_number
- preferred_channel
- created_at
- updated_at

## companies
- id
- user_id
- company_name
- company_number
- company_status
- incorporation_date
- registered_office_address
- sic_codes_json
- accounts_due_date
- confirmation_statement_due_date
- last_synced_at
- created_at
- updated_at

## reminders
- id
- user_id
- company_id nullable
- reminder_type
- reminder_date
- channel
- status
- created_at
- updated_at

## conversations
- id
- user_id
- channel
- external_thread_id
- created_at
- updated_at

## messages
- id
- conversation_id
- sender_type
- agent_name nullable
- message_text
- created_at

## tool_call_logs
- id
- conversation_id
- agent_name
- tool_name
- tool_input_json
- tool_output_json
- success
- created_at

## receipts
- id
- user_id
- file_url
- merchant
- receipt_date
- total_amount
- tax_amount
- currency
- extracted_json
- extraction_confidence
- created_at
- updated_at

## transactions
- id
- user_id
- source
- txn_date
- description
- amount
- currency
- category
- category_confidence
- is_verified
- created_at
- updated_at