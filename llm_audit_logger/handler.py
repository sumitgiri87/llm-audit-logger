"""
LangChain / LangGraph callback handler.

Attach to any agent to capture every callback event as an AuditEvent and write
it through AuditLogWriter:

    from llm_audit_logger import AuditCallbackHandler
    handler = AuditCallbackHandler(output_dir="./audit_logs")
    agent_executor = AgentExecutor(agent=agent, tools=tools, callbacks=[handler])

``langchain-core`` is imported lazily: if it is not installed, a minimal base
class is used so the package still imports and the core writer remains usable.
"""
from __future__ import annotations

import json
import time
from typing import Any

from llm_audit_logger.schema import EventType
from llm_audit_logger.writer import AuditLogWriter

try:  # exercised only when langchain-core is installed
    from langchain_core.callbacks import BaseCallbackHandler

    _HAS_LANGCHAIN = True
except Exception:  # langchain-core not installed
    class BaseCallbackHandler:  # minimal shim so the package imports cleanly
        pass

    _HAS_LANGCHAIN = False


def _safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


class AuditCallbackHandler(BaseCallbackHandler):
    """Drop-in LangChain callback handler that writes a structured audit trail."""

    def __init__(self, output_dir: str = "./audit_logs", session_id=None, metadata=None):
        self.writer = AuditLogWriter(output_dir=output_dir, session_id=session_id)
        self.base_metadata = metadata or {}
        self._starts: dict = {}  # run_id -> start time, for latency

    # ---- helpers -------------------------------------------------------
    def _meta(self, extra=None):
        m = dict(self.base_metadata)
        if extra:
            m.update(extra)
        return m

    @staticmethod
    def _rid(run_id):
        return str(run_id) if run_id is not None else None

    def _latency(self, run_id):
        start = self._starts.pop(str(run_id), None)
        return round((time.time() - start) * 1000, 1) if start else None

    # ---- LLM -----------------------------------------------------------
    def on_llm_start(self, serialized, prompts, *, run_id=None, parent_run_id=None, **kw):
        self._starts[str(run_id)] = time.time()

    def on_llm_end(self, response, *, run_id=None, parent_run_id=None, **kw):
        try:
            completion = response.generations[0][0].text
        except Exception:
            completion = str(response)
        self.writer.emit(
            EventType.LLM_CALL,
            completion=completion,
            latency_ms=self._latency(run_id),
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta(),
        )

    # ---- Tools ---------------------------------------------------------
    def on_tool_start(self, serialized, input_str, *, run_id=None, parent_run_id=None, **kw):
        self._starts[str(run_id)] = time.time()
        self.writer.emit(
            EventType.TOOL_CALL,
            tool_name=(serialized or {}).get("name"),
            tool_input=_safe(input_str),
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta(),
        )

    def on_tool_end(self, output, *, run_id=None, parent_run_id=None, **kw):
        self.writer.emit(
            EventType.TOOL_RESULT,
            tool_output=_safe(output),
            latency_ms=self._latency(run_id),
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta(),
        )

    # ---- Chain / Agent -------------------------------------------------
    def on_chain_start(self, serialized, inputs, *, run_id=None, parent_run_id=None, **kw):
        self.writer.emit(
            EventType.CHAIN_START,
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta({"inputs": _safe(inputs)}),
        )

    def on_chain_end(self, outputs, *, run_id=None, parent_run_id=None, **kw):
        self.writer.emit(
            EventType.CHAIN_END,
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta({"outputs": _safe(outputs)}),
        )

    def on_agent_action(self, action, *, run_id=None, parent_run_id=None, **kw):
        self.writer.emit(
            EventType.AGENT_ACTION,
            tool_name=getattr(action, "tool", None),
            tool_input=_safe(getattr(action, "tool_input", None)),
            reasoning_chain=[getattr(action, "log", "")],
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta(),
        )

    def on_agent_finish(self, finish, *, run_id=None, parent_run_id=None, **kw):
        self.writer.emit(
            EventType.AGENT_FINISH,
            completion=str(getattr(finish, "return_values", finish)),
            run_id=self._rid(run_id),
            parent_run_id=self._rid(parent_run_id),
            metadata=self._meta(),
        )
