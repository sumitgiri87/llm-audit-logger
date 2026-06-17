"""
Audit event schema (v1).

Implemented as a stdlib dataclass so the core has zero dependencies. The field
set maps directly to OSFI E-23 and EU AI Act Article 12 record-keeping needs:
who did what, when, with which model, on what input, producing what output.
Every field that is not relevant to a given event type stays ``None`` and is
omitted from the serialized line.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


class EventType:
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CHAIN_START = "chain_start"
    CHAIN_END = "chain_end"
    AGENT_ACTION = "agent_action"
    AGENT_FINISH = "agent_finish"

    ALL = {
        LLM_CALL, TOOL_CALL, TOOL_RESULT, CHAIN_START,
        CHAIN_END, AGENT_ACTION, AGENT_FINISH,
    }


@dataclass
class AuditEvent:
    session_id: str
    event_type: str
    timestamp_utc: str

    model: Optional[str] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None

    tool_name: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_output: Optional[Any] = None
    reasoning_chain: Optional[list] = None

    token_count_prompt: Optional[int] = None
    token_count_completion: Optional[int] = None
    latency_ms: Optional[float] = None

    run_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_type not in EventType.ALL:
            raise ValueError(f"unknown event_type: {self.event_type!r}")

    def to_dict(self) -> dict:
        """Drop None fields so each line carries only what is relevant."""
        return {k: v for k, v in asdict(self).items() if v is not None}
