# llm-audit-logger

![Status](https://img.shields.io/badge/status-active--development-orange)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Stack](https://img.shields.io/badge/stack-LangChain%20%7C%20LangGraph-informational)
![Regulatory](https://img.shields.io/badge/regulatory-OSFI%20E--23%20%7C%20EU%20AI%20Act-darkgreen)

> Drop-in Python middleware that gives your LangChain agent a tamper-evident, compliance-ready audit trail in one import.

> **Part of the [agentic-ai-security-audit-framework](https://github.com/sumitgiri/agentic-ai-security-audit-framework) — a structured methodology for auditing enterprise agentic AI deployments.**

---

## Table of Contents

1. [The Governance Problem](#1-the-governance-problem)
2. [What the Logger Captures](#2-what-the-logger-captures)
3. [Quickstart](#3-quickstart)
4. [Output Schema](#4-output-schema)
5. [This vs LangSmith](#5-this-vs-langsmith)
6. [Regulatory Context](#6-regulatory-context)
7. [Installation](#7-installation)
8. [Repository Structure](#8-repository-structure)
9. [Current Status](#9-current-status)
10. [Related Repos](#10-related-repos)
11. [References](#11-references)
12. [Author](#12-author)

---

## 1. The Governance Problem

Enterprises deploying LangChain and LangGraph agents in production have a documentation gap they have not yet priced in.

OSFI Guideline E-23 requires federally regulated financial institutions to maintain evidence of model behaviour — decisions made, inputs processed, outputs produced — as part of ongoing model risk management. The May 2027 deadline is not far. EU AI Act Article 13 requires high-risk AI systems to produce logs sufficient to enable post-hoc evaluation of system behaviour.

Neither requirement can be satisfied by what most teams currently have, which is: nothing structured, or a LangSmith dashboard that was built for engineers, not auditors.

When an agent calls a tool, retrieves a document, reasons over context, and produces an output, that sequence of events needs to be recorded in a form that:

- Is tamper-evident and timestamped
- Captures the full input/output at every step, not just the final response
- Records which model version made which decision
- Links every action to a session, user, and timestamp
- Is structured enough for a compliance officer or external auditor to read without needing to understand LangChain internals

Right now, most production deployments produce none of this. This library produces all of it, with one import.

---

## 2. What the Logger Captures

Every log entry written by `llm-audit-logger` captures:

| Field | Description |
|---|---|
| `session_id` | Unique identifier for the agent session |
| `event_type` | `llm_call` \| `tool_call` \| `tool_result` \| `chain_start` \| `chain_end` \| `agent_action` \| `agent_finish` |
| `timestamp_utc` | ISO 8601, UTC, microsecond precision |
| `model` | Model identifier and version string (e.g. `gpt-4o-2024-08-06`) |
| `prompt` | Full prompt sent to the model at this step |
| `completion` | Full model output at this step |
| `tool_name` | Name of the tool invoked (for `tool_call` events) |
| `tool_input` | Exact input passed to the tool |
| `tool_output` | Exact output returned by the tool |
| `reasoning_chain` | Agent's intermediate reasoning steps (where available) |
| `token_count_prompt` | Prompt token count |
| `token_count_completion` | Completion token count |
| `latency_ms` | Time from request to response in milliseconds |
| `parent_run_id` | Links child events to parent chain for full trace reconstruction |
| `metadata` | Passthrough dict for application-defined context (user ID, request ID, environment) |

Nothing is sampled. Nothing is summarised. Every event in every agent run is written to the log in full.

---

## 3. Quickstart

```python
from llm_audit_logger import AuditCallbackHandler
from langchain.agents import AgentExecutor

# Attach to any existing LangChain agent — no other changes required
audit_handler = AuditCallbackHandler(output_dir="./audit_logs")
agent_executor = AgentExecutor(agent=agent, tools=tools, callbacks=[audit_handler])

result = agent_executor.invoke({"input": "Summarise last quarter's risk report"})
```

That is the entire integration. The handler intercepts every LangChain callback event and writes structured JSON to `./audit_logs/`. Existing agent logic is unchanged.

**LangGraph integration is in progress** — see [Current Status](#9-current-status). The callback pattern is the same; integration will be added once the core handler is validated.

---

## 4. Output Schema

Each agent run produces a newline-delimited JSON file (one event per line) named `{session_id}_{timestamp}.jsonl`.

```json
{
  "session_id": "sess_a3f9c2e1",
  "event_type": "tool_call",
  "timestamp_utc": "2025-03-14T10:42:01.334891Z",
  "model": "gpt-4o-2024-08-06",
  "tool_name": "document_retriever",
  "tool_input": {
    "query": "OSFI E-23 model validation requirements"
  },
  "tool_output": {
    "chunks_retrieved": 4,
    "sources": ["osfi_e23_section_4.pdf", "osfi_e23_section_7.pdf"],
    "content_preview": "Model validation must be conducted by personnel independent of..."
  },
  "latency_ms": 312,
  "parent_run_id": "run_7b1d4a88",
  "metadata": {
    "user_id": "analyst_042",
    "environment": "production",
    "application": "risk-review-agent"
  }
}
```

```json
{
  "session_id": "sess_a3f9c2e1",
  "event_type": "llm_call",
  "timestamp_utc": "2025-03-14T10:42:02.109441Z",
  "model": "gpt-4o-2024-08-06",
  "prompt": "Based on the retrieved documents, summarise the validation requirements...",
  "completion": "OSFI E-23 Section 4 requires that model validation be conducted by...",
  "token_count_prompt": 1842,
  "token_count_completion": 394,
  "latency_ms": 1204,
  "parent_run_id": "run_7b1d4a88",
  "metadata": {
    "user_id": "analyst_042",
    "environment": "production",
    "application": "risk-review-agent"
  }
}
```

The `.jsonl` format is chosen deliberately: it is appendable, line-parseable, and ingestible directly by SIEM tools, S3-based log pipelines, and compliance evidence management systems without transformation.

---

## 5. This vs LangSmith

LangSmith is excellent at what it does. This library does something different.

| | LangSmith | llm-audit-logger |
|---|---|---|
| **Primary audience** | Developers | Compliance officers, auditors, regulators |
| **Purpose** | Debug, evaluate, improve agent performance | Produce tamper-evident compliance evidence |
| **Schema** | Optimised for developer inspection | Optimised for regulatory documentation requirements |
| **Retention** | Managed by LangChain (cloud) | You own the logs, you control retention |
| **Data residency** | LangChain infrastructure | Your infrastructure — on-prem, private VPC, or cloud of choice |
| **Regulatory mapping** | None | Fields map directly to OSFI E-23 and EU AI Act documentation requirements |
| **Access control** | LangSmith project permissions | Your own access controls |
| **Dependency** | Requires LangChain stack | Works with LangChain; adapter pattern supports other stacks |

The practical difference: a LangSmith trace answers "what did my agent do and why did it perform poorly?" An `llm-audit-logger` log answers "did this agent operate within its authorised boundaries, and can I prove it to a regulator?"

For a Canadian bank subject to OSFI E-23, the second question is the one with a compliance deadline attached.

---

## 6. Regulatory Context

### OSFI Guideline E-23 — Model Risk Management

E-23 requires federally regulated financial institutions to maintain documentation of model behaviour as part of ongoing model risk management. This includes evidence of what inputs models received, what outputs they produced, and whether outputs were within expected parameters. For agentic AI systems, this extends to every tool call, retrieval step, and decision point in the agent's execution chain. Compliance deadline: **May 2027.**

### EU AI Act — Article 13 (Transparency) and Article 12 (Record-Keeping)

Article 12 requires high-risk AI systems to automatically log events sufficient to enable post-hoc assessment of system behaviour. Article 13 requires that high-risk AI systems are transparent enough that users can interpret outputs appropriately. The structured log produced by this library is designed to satisfy Article 12 logging requirements directly.

### What this means in practice

If your organisation is deploying agentic AI and is subject to either of these instruments, you need a log that an auditor can read. Not a dashboard. Not a trace viewer. A structured, exportable, human-readable record of every decision the agent made and every action it took. That is what this library produces.

---

## 7. Installation

Install from source while the package is in active development:

```bash
git clone https://github.com/sumitgiri/llm-audit-logger
cd llm-audit-logger
pip install -e .
```

PyPI package will be published once the core handler and schema are stable — see [Current Status](#9-current-status).

**Dependencies:** `langchain-core >= 0.1.0`, `pydantic >= 2.0`

No external services. No API keys. Logs write to local filesystem by default. S3 and GCS output adapters are planned.

---

## 8. Repository Structure

The library is being built handler-first — core callback integration before output adapters, local filesystem before cloud storage.

**Current:** `AuditCallbackHandler` core, JSONL writer, Pydantic schema v1.  
**In progress:** LangGraph callback integration, examples.  
**Planned:** S3 and GCS adapters, OSFI E-23 and EU AI Act field mapping documentation.

---

## 9. Current Status

| Component | Status |
|---|---|
| `AuditCallbackHandler` core | 🔄 In progress |
| JSONL file writer | 🔄 In progress |
| Pydantic schema v1 | 🔄 In progress |
| LangGraph callback integration | 🔄 In progress |
| S3 output adapter | 📅 Planned |
| GCS output adapter | 📅 Planned |
| OSFI E-23 field mapping documentation | 📅 Planned |
| EU AI Act Article 12 field mapping documentation | 📅 Planned |

---

## 10. Related Repos

| Repository | Description |
|---|---|
| [agentic-ai-security-audit-framework](https://github.com/sumitgiri/agentic-ai-security-audit-framework) | Flagship repo — full audit methodology, compliance mapper, evidence templates |
| [agentic-rag-security-lab](https://github.com/sumitgiri/agentic-rag-security-lab) | Vulnerable-by-design RAG pipeline for attack research |
| agent-compliance-mapper | CLI tool for EU AI Act and OSFI E-23 gap analysis *(coming)* |
| llm-audit-logger | **This repo** |

---

## 11. References

- OSFI Guideline E-23 — *Model Risk Management* (revised, effective May 2027). Office of the Superintendent of Financial Institutions, Canada.
- EU Artificial Intelligence Act (Regulation 2024/1689) — Article 12 (Record-Keeping), Article 13 (Transparency). European Parliament, August 2024.
- LangChain Callbacks Documentation — BaseCallbackHandler interface.
- NIST AI RMF — Measure 2.5: AI system behavior is monitored.

---

## 12. Author

**Sumit Giri**  
Security Engineer · AI Red Teamer · PhD Mathematics (Cryptography)  
Toronto, Ontario, Canada

AI red teaming at Mindrift. Cybersecurity consulting at CyStack. Building an independent AI agent security audit practice for Canadian regulated enterprises.

[LinkedIn](https://linkedin.com/in/sumitgiri) · [GitHub](https://github.com/sumitgiri)

---

*This is independent research. No vendor relationship. No affiliation with any of the frameworks or organisations referenced.*
