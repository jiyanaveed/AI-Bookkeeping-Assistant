# Cursor Master Prompt

Build a new Python backend project for a UK AI Accountant Agent using:
- FastAPI
- OpenAI Agents SDK
- Companies House REST API
- PostgreSQL or SQLite for initial persistence

Implement a 4-agent architecture:

1. Intake Agent
- collects raw user data from chat and documents
- extracts structured fields
- identifies missing data

2. Bookkeeping Agent
- handles transaction categorization
- calculations
- monthly summaries
- bookkeeping logic

3. Compliance Agent
- handles UK company search
- Companies House profile lookup
- deadline retrieval
- filing awareness
- reminders

4. Supervisor Agent
- routes tasks to specialist agents
- validates specialist outputs
- blocks hallucinated answers
- merges final response
- enforces confirmation before actions

Important architecture rules:
- do not call all 4 agents on every request
- route intelligently
- use Supervisor Agent as final user-facing layer
- tools are the source of truth
- never guess company deadlines or filing status
- reminder creation must require explicit confirmation

Implement these tools first:
- search_company_by_name
- get_company_profile
- get_company_deadlines
- get_company_filing_history
- create_reminder
- list_upcoming_deadlines

Implement first working flow only:
company search -> verified deadlines -> plain-English summary -> optional reminder after confirmation

Create a clean project structure with:
- app/main.py
- app/agents/
- app/tools/
- app/services/
- app/models/
- app/config/
- tests/

Add environment variable support for:
- OPENAI_API_KEY
- COMPANIES_HOUSE_API_KEY
- DATABASE_URL

Return:
1. project structure
2. all created files
3. exact run instructions
4. exact env variables required
5. simple local test instructions

Do not build Slack or WhatsApp yet.
Do not build a frontend yet.
Focus on a reliable backend-first agent service.
