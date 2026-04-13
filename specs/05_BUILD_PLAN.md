# Build Plan — Cursor Implementation

## Objective
Build a new backend-first AI accountant agent using OpenAI Agents SDK.

## Phase 1 — Core Agent
Build:
- FastAPI backend
- OpenAI Agents SDK integration
- 4-agent architecture
- Supervisor Agent as final response layer
- Companies House REST integration
- first working flow:
  company search -> deadline retrieval -> response -> optional reminder

## Phase 2 — Receipt Intake
Build:
- receipt upload endpoint
- receipt parsing
- Intake Agent structured extraction
- handoff into Bookkeeping Agent

## Phase 3 — Bookkeeping
Build:
- transaction store
- categorization
- monthly summaries
- reconciliation helpers

## Phase 4 — Channels
Build:
- Slack webhook adapter
- WhatsApp webhook adapter
- shared message normalization layer

## Coding Rules
- backend is source of truth
- tools must be typed and testable
- no fake production logic
- action tools require confirmation
- log all tool calls
- keep code modular and boring

## First Demo Requirement
User can ask:
"Find Tesco PLC and tell me the next important Companies House deadlines."

System should:
- search company
- fetch profile
- fetch deadlines
- summarize clearly
- offer reminder creation