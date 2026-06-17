"""
llm-audit-logger - tamper-evident, compliance-ready audit trail for LLM agents.

The core (schema + writer) has **zero dependencies** and runs on the Python
standard library, so it can produce and verify audit logs anywhere. The
LangChain/LangGraph callback handler imports ``langchain-core`` lazily, so this
package imports cleanly with or without the LangChain stack installed.

    from llm_audit_logger import AuditCallbackHandler   # for LangChain agents
    from llm_audit_logger import AuditLogWriter, AuditEvent, EventType, verify_log
"""
from __future__ import annotations

from llm_audit_logger.handler import AuditCallbackHandler
from llm_audit_logger.schema import AuditEvent, EventType
from llm_audit_logger.writer import AuditLogWriter, verify_log

__all__ = [
    "AuditCallbackHandler",
    "AuditLogWriter",
    "AuditEvent",
    "EventType",
    "verify_log",
]

__version__ = "0.1.0"
