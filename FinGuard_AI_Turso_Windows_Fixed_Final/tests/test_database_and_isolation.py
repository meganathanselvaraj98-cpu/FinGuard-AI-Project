from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from backend.database import initialize_database, session_scope
from backend.models import AuditLog, Transaction
from backend.services import add_transaction, list_transactions, register_user


def test_user_transaction_isolation_and_audit_logs():
    initialize_database()
    with session_scope() as session:
        first = register_user(session, "First Demo User", "first.isolation@example.com", "Strong@123")
        second = register_user(session, "Second Demo User", "second.isolation@example.com", "Strong@123")
        session.flush()
        add_transaction(session, first.id, {"transaction_date": datetime(2026, 1, 1), "description": "First salary", "transaction_type": "INCOME", "amount": 50000, "category": "Salary", "transaction_id": "ISO-FIRST"})
        add_transaction(session, second.id, {"transaction_date": datetime(2026, 1, 2), "description": "Second salary", "transaction_type": "INCOME", "amount": 60000, "category": "Salary", "transaction_id": "ISO-SECOND"})
        session.flush()
        first_rows = list_transactions(session, first.id)
        second_rows = list_transactions(session, second.id)
        assert len(first_rows) == 1 and first_rows[0].user_id == first.id
        assert len(second_rows) == 1 and second_rows[0].user_id == second.id
        assert first_rows[0].transaction_id_encrypted != "ISO-FIRST"
        assert session.scalar(select(AuditLog).where(AuditLog.user_id == first.id)) is not None
        assert session.scalar(select(Transaction).where(Transaction.user_id == first.id, Transaction.user_id == second.id)) is None
