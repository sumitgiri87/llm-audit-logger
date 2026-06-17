"""
JSONL audit-log writer with a tamper-evident hash chain.

Each event is written as one JSON line. Every line carries ``prev_hash`` and
``record_hash``, where ``record_hash = sha256(prev_hash + canonical_event)``.
Because each record commits to the previous one, removing, reordering, or
editing any line breaks the chain from that point onward - which ``verify_log``
detects. This is the "tamper-evident" property auditors ask for; for stronger
guarantees, write to immutable storage (S3 Object Lock) and periodically anchor
the latest ``record_hash`` externally.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from llm_audit_logger.schema import AuditEvent

GENESIS = "0" * 64


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(payload)).encode("utf-8")).hexdigest()


class AuditLogWriter:
    """Append-only JSONL writer, one file per session, with a hash chain."""

    def __init__(self, output_dir: str = "./audit_logs", session_id: str | None = None):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.session_id = session_id or (
            "sess_" + hashlib.sha1(_utc_now_iso().encode()).hexdigest()[:8]
        )
        ts = _utc_now_iso().replace(":", "").replace(".", "")
        self.path = os.path.join(output_dir, f"{self.session_id}_{ts}.jsonl")
        self._prev_hash = GENESIS

    def write(self, event: AuditEvent) -> dict:
        payload = event.to_dict()
        record = dict(payload)
        record["prev_hash"] = self._prev_hash
        record["record_hash"] = _hash(self._prev_hash, payload)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(_canonical(record) + "\n")
        self._prev_hash = record["record_hash"]
        return record

    def emit(self, event_type: str, **fields) -> dict:
        """Build an AuditEvent for this session and write it in one call."""
        event = AuditEvent(
            session_id=self.session_id,
            event_type=event_type,
            timestamp_utc=_utc_now_iso(),
            **fields,
        )
        return self.write(event)


def verify_log(path: str) -> bool:
    """Re-walk a log file and confirm the hash chain is intact and untampered."""
    prev = GENESIS
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            stored_hash = record.pop("record_hash", None)
            claimed_prev = record.pop("prev_hash", None)
            if claimed_prev != prev:
                return False
            if _hash(prev, record) != stored_hash:
                return False
            prev = stored_hash
    return True
