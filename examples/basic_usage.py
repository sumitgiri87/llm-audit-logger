"""
Runnable offline example - no LangChain, no API key.

Simulates an agent run by emitting audit events directly through AuditLogWriter,
then prints the JSONL file and verifies the tamper-evident hash chain.

    python examples/basic_usage.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_audit_logger import AuditLogWriter, EventType, verify_log  # noqa: E402


def main() -> None:
    writer = AuditLogWriter(output_dir="./audit_logs", session_id="sess_demo01")

    writer.emit(EventType.CHAIN_START, metadata={"application": "risk-review-agent"})
    writer.emit(
        EventType.TOOL_CALL,
        tool_name="document_retriever",
        tool_input={"query": "OSFI E-23 model validation requirements"},
        metadata={"user_id": "analyst_042", "environment": "production"},
    )
    writer.emit(
        EventType.TOOL_RESULT,
        tool_name="document_retriever",
        tool_output={"chunks_retrieved": 4, "sources": ["osfi_e23_s4.pdf"]},
        latency_ms=312,
    )
    writer.emit(
        EventType.LLM_CALL,
        model="gpt-4o-2024-08-06",
        prompt="Summarise the validation requirements...",
        completion="OSFI E-23 Section 4 requires independent validation...",
        token_count_prompt=1842,
        token_count_completion=394,
        latency_ms=1204,
    )
    writer.emit(EventType.AGENT_FINISH, completion="Done.")

    print(f"wrote audit log -> {writer.path}\n")
    with open(writer.path, encoding="utf-8") as fh:
        for line in fh:
            print(line.rstrip())

    print("\nhash chain intact:", verify_log(writer.path))


if __name__ == "__main__":
    main()
