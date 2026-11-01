"""Approval workflow enforcement — the AI-control requirements in test form:

  * an unapproved proposal must NEVER be activatable
  * rejecting leaves the active plan unchanged
  * the latest decision wins (approve then reject → still blocked)
  * activation_allowed flips only after an explicit approve
"""
import pytest

from src.services import approvals


class FakeStore:
    """In-memory stand-in with the exact decision protocol of the real stores."""

    def __init__(self):
        self.rows = []
        self._seq = 0

    def record_decision(self, proposal_id: str, action: str, notes: str = "") -> str:
        if action not in ("approve", "reject", "edit"):
            raise ValueError(f"invalid action {action}")
        self._seq += 1
        self.rows.append({"id": f"d{self._seq}", "proposal_id": proposal_id,
                          "action": action, "notes": notes,
                          "decided_at": f"2026-01-0{self._seq}T10:00:00"})
        return f"d{self._seq}"

    def list_decisions(self, limit: int = 50) -> list[dict]:
        return list(self.rows)


def test_unapproved_proposal_cannot_activate():
    store = FakeStore()
    assert approvals.activation_allowed(store, "p1") is False
    with pytest.raises(PermissionError):
        approvals.guard_activate(store, "p1")


def test_rejection_leaves_plan_unchanged_and_blocked():
    store = FakeStore()
    store.record_decision("p1", "reject", "not this week")
    assert approvals.activation_allowed(store, "p1") is False
    with pytest.raises(PermissionError):
        approvals.guard_activate(store, "p1")


def test_explicit_approval_activates_then_latest_wins():
    store = FakeStore()
    store.record_decision("p1", "approve")
    assert approvals.activation_allowed(store, "p1") is True
    # a later reject revokes it — history is kept, latest rules
    store.record_decision("p1", "reject")
    assert approvals.activation_allowed(store, "p1") is False


def test_reapprove_after_reject_restores_activation():
    store = FakeStore()
    store.record_decision("p1", "reject")
    store.record_decision("p1", "approve")
    assert approvals.activation_allowed(store, "p1") is True


def test_edited_decision_counts_as_user_approved():
    store = FakeStore()
    store.record_decision("p1", "edit", "trimmed to 3 items")
    assert approvals.activation_allowed(store, "p1") is True


def test_decisions_are_isolated_per_proposal():
    store = FakeStore()
    store.record_decision("p1", "approve")
    assert approvals.activation_allowed(store, "p2") is False


def test_invalid_action_rejected_at_the_door():
    store = FakeStore()
    with pytest.raises(ValueError):
        approvals.record_decision(store, proposal_id="p3", action="silent_apply")


def test_record_decision_returns_persisted_row():
    store = FakeStore()
    out = approvals.record_decision(store, proposal_id="p4", action="approve",
                                    notes="ok")
    assert out["recorded"] is True and out["proposal_id"] == "p4"
    assert any(r["id"] == out["id"] for r in store.list_decisions())
