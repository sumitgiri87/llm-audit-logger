"""Offline tests for the audit writer and tamper-evidence (stdlib only)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_audit_logger import AuditLogWriter, EventType, verify_log  # noqa: E402


def _writer(directory):
    return AuditLogWriter(output_dir=directory, session_id="sess_test")


def test_writes_one_line_per_event():
    with tempfile.TemporaryDirectory() as d:
        w = _writer(d)
        w.emit(EventType.TOOL_CALL, tool_name="t", tool_input={"q": "x"})
        w.emit(EventType.LLM_CALL, completion="hello")
        lines = [ln for ln in open(w.path) if ln.strip()]
        assert len(lines) == 2
        assert json.loads(lines[0])["event_type"] == "tool_call"


def test_none_fields_are_omitted():
    with tempfile.TemporaryDirectory() as d:
        w = _writer(d)
        rec = w.emit(EventType.LLM_CALL, completion="hi")
        assert "tool_name" not in rec and "prompt" not in rec


def test_hash_chain_verifies():
    with tempfile.TemporaryDirectory() as d:
        w = _writer(d)
        for i in range(5):
            w.emit(EventType.LLM_CALL, completion=f"r{i}")
        assert verify_log(w.path) is True


def test_tampering_is_detected():
    with tempfile.TemporaryDirectory() as d:
        w = _writer(d)
        w.emit(EventType.LLM_CALL, completion="original")
        w.emit(EventType.LLM_CALL, completion="second")
        lines = open(w.path).readlines()
        lines[0] = lines[0].replace("original", "edited")
        with open(w.path, "w") as fh:
            fh.writelines(lines)
        assert verify_log(w.path) is False


def test_unknown_event_type_rejected():
    with tempfile.TemporaryDirectory() as d:
        w = _writer(d)
        try:
            w.emit("not_a_real_event")
            assert False, "should have raised ValueError"
        except ValueError:
            pass
