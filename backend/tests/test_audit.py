"""Audit persistence must retain metadata, never raw model content."""

from sqlalchemy import delete, select

from app.db.models import AuditEvent
from app.db.session import SessionLocal
from app.guardrails.runtime import record_audit


def test_audit_event_is_deidentified_and_persisted():
    record_audit(
        kind="test.audit",
        status="ok",
        subject="private-session-value",
        agent_id="guide",
        input_chars=99,
        output_chars=100,
        metadata={"poi_id": "poi_0001"},
    )
    with SessionLocal() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.kind == "test.audit"))
        assert event is not None
        assert event.subject_hash != "private-session-value"
        assert event.input_chars == 99
        assert event.output_chars == 100
        assert event.metadata_json == {"poi_id": "poi_0001"}
        session.execute(delete(AuditEvent).where(AuditEvent.kind == "test.audit"))
        session.commit()
