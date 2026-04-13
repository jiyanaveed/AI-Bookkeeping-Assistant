# Agent Architecture — UK AI Accountant Agent

## Recommended Multi-Agent Design

The system uses 4 agents.

### 1. Intake Agent
Purpose:
- collect raw user data
- understand user intent
- extract structured fields from messages
- read receipts, invoices, and uploaded financial documents
- identify what information is missing

Responsibilities:
- parse user chat into structured tasks
- extract company name, company number, dates, amounts, merchant names, invoice details
- OCR/parse receipt fields where available
- ask follow-up questions only when essential
- pass structured output to downstream agents

Input examples:
- "Find my company deadlines"
- "Scan this receipt"
- "How much did I spend this month?"
- uploaded receipt/invoice/document

Output examples:
- normalized task type
- extracted entities
- missing fields
- confidence score

### 2. Bookkeeping Agent
Purpose:
- perform bookkeeping logic and financial calculations

Responsibilities:
- categorize transactions
- create monthly summaries
- compute totals
- identify uncategorized items
- reconcile structured receipt data with transactions
- prepare accountant-ready summaries

Rules:
- never invent numbers
- clearly label estimated vs verified values
- calculations must come from tool data or explicit user data

### 3. Compliance Agent
Purpose:
- handle company deadlines, filings, reminders, and compliance awareness

Responsibilities:
- search UK companies
- fetch Companies House profile
- fetch filing history
- determine important due dates
- detect overdue or near-due items
- prepare reminders

Rules:
- never guess deadlines from memory
- always use tools for company lookup and deadlines
- if no verified deadline is available, say so directly

### 4. Supervisor Agent
Purpose:
- govern agent routing, validation, and final response assembly

Responsibilities:
- decide which specialist agent(s) should handle the task
- validate that specialist outputs are grounded
- reject weak or hallucinated outputs
- merge outputs into one user-facing response
- enforce confirmation before action tools
- keep responses concise, practical, and safe

Important:
The Supervisor Agent should NOT re-do every specialist task from scratch.
It should:
- validate
- resolve conflicts
- block unsafe answers
- compose the final answer

## Routing Rules

### Route to Intake Agent when:
- raw user message arrives
- uploaded receipt/document arrives
- task is ambiguous
- fields need extraction

### Route to Bookkeeping Agent when:
- user asks about spending
- user asks for financial totals or summaries
- receipt/transaction data has already been extracted
- classification/calculation is needed

### Route to Compliance Agent when:
- user asks about company lookup
- user asks about Companies House deadlines
- user asks about filings
- reminders are needed for deadlines

### Route to Supervisor Agent always for:
- final response approval
- action approval checks
- conflict resolution
- safety validation

## Initial Deployment Strategy

For v1:
- keep all 4 agents in code
- but only fully activate the Compliance workflow first
- Bookkeeping and Intake receipt scanning can remain partial if needed
- Supervisor should be the only agent that responds directly to the user

## Latency / Cost Control
Do NOT call all 4 agents for every message.

Preferred flow:
- Intake routes
- one specialist handles the main task
- Supervisor validates and responds

Only call multiple specialists when genuinely needed.