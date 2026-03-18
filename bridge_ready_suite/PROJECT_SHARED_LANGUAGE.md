# PROJECT SHARED LANGUAGE — Floor Plan AI

## Purpose
This document defines the shared language, contracts, and structure used across all chats and components in the "Floor Plan AI" project.

It ensures alignment between:
- Floor Plan AI (Orchestrator)
- MCP Bridge
- Codex Executor
- All ChatGPT sessions within the project

This document is the SOURCE OF TRUTH for naming, structure, and communication.

---

# 1. Core System Components

## 1.1 Floor Plan AI (Main System)
The overall product/system.

Responsibilities:
- Receive user input
- Understand intent
- Decompose tasks
- Orchestrate execution
- Validate results
- Produce final outputs

---

## 1.2 Orchestrator
Logical component inside Floor Plan AI.

Responsibilities:
- Break user requests into structured tasks
- Decide when to call Codex
- Manage execution flow
- Handle retries / iteration
- Aggregate results

---

## 1.3 MCP Bridge
Integration layer between ChatGPT and Codex.

Responsibilities:
- Expose tools
- Transport structured tasks
- Enforce contracts
- Handle execution lifecycle
- Return structured results

---

## 1.4 Codex Executor
Execution engine.

Responsibilities:
- Execute tasks
- Generate artifacts (code / JSON / analysis / etc.)
- Follow constraints
- Return structured results

---

# 2. Core Concepts

## 2.1 Task Spec
A structured definition of work sent to Codex.

### Required Structure:
1. Objective
2. Scope
3. Inputs
4. Constraints
5. Expected Outputs
6. Validation Rules
7. Failure Conditions
8. Notes / Context

---

## 2.2 Artifact
Any output produced by the system.

Examples:
- Code (C#, Python, etc.)
- JSON structures
- CSV datasets
- Floor plan representations
- Reports
- Prompts
- Validation outputs

---

## 2.3 Execution Result
The structured response returned from Codex.

### Standard Structure:
- status: success | partial_success | failure
- artifacts: list of produced artifacts
- logs: execution notes
- errors: list of issues (if any)
- validation_summary: pass/fail + explanation
- recommendations: optional next steps

---

## 2.4 Validation Rules
Rules used to determine if a result is acceptable.

Examples:
- schema validation
- geometry consistency
- required fields present
- constraints respected
- business rules satisfied

---

## 2.5 Source of Truth
All official project decisions and definitions.

Includes:
- this document
- architecture docs
- MCP contracts
- agreed schemas

Chats are NOT source of truth.

---

# 3. Execution Flow

## Standard Flow:

1. User Input
2. Orchestrator interprets intent
3. Orchestrator creates Task Spec
4. Task Spec sent via MCP Bridge
5. Codex executes task
6. Codex returns Execution Result
7. Orchestrator validates result
8. If needed → iterate (new Task Spec)
9. Final result returned to user

---

# 4. Contract Principles

## 4.1 Always Structured
No free-form execution requests.

Everything must be:
- explicit
- structured
- machine-readable

---

## 4.2 No Hidden Assumptions
All inputs must be declared.

No reliance on:
- chat memory
- implicit knowledge
- previous messages

---

## 4.3 Deterministic Outputs
Outputs should be:
- predictable
- structured
- testable

---

## 4.4 Explicit Failure Handling
Every task must define:
- what failure is
- what partial success is
- what to do next

---

# 5. Standard Response Formats

## 5.1 Design / Architecture Response

Use this format:

1. Decision  
2. Why  
3. Assumptions  
4. Risks  
5. Required Contract / Interface  
6. Next Step  

---

## 5.2 Task Spec (Execution Request)

Use this format:

1. Objective  
2. Scope  
3. Inputs  
4. Constraints  
5. Expected Outputs  
6. Validation Rules  
7. Failure Conditions  
8. Notes / Context  

---

## 5.3 Execution Result (Codex Response)

Must include:

- status
- artifacts
- logs
- errors
- validation_summary
- recommendations (optional)

---

# 6. Responsibilities Separation

## Floor Plan AI / Orchestrator
- owns logic
- owns flow
- owns decisions
- defines tasks

## MCP Bridge
- owns transport
- owns contracts
- owns execution lifecycle

## Codex
- owns execution
- owns artifact generation

---

# 7. Rules for All Chats

- Do NOT assume cross-chat memory
- Always refer to shared definitions
- Prefer structure over free text
- Be explicit and unambiguous
- If something is unclear → define it
- If something is missing → ask or propose

---

# 8. Evolution Rule

If a concept changes:
- Update this document
- Treat update as official
- Align all chats to it

---

# END OF DOCUMENT