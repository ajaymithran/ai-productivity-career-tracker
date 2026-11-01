"""Approval workflow service — the enforcement point of the AI rules.

Invariant: nothing in the application (AI or otherwise) may activate a plan
or change live tasks unless a decision row exists here with action='approve'.
The service records decisions in whichever store is active; history is
permanent and queryable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Proposal:
    id: str
    text: str
    status: str = "pending"            # pending | approved | rejected | edited
    decided_at: str | None = None
    decisions: list = field(default_factory=list)


def record_decision(store, *, proposal_id: str, action: str, notes: str = "") -> dict:
    """Persist a decision. store = data source abstraction.
    Returns the recorded decision for immediate UI feedback."""
    if action not in ("approve", "reject", "edit"):
        raise ValueError(f"invalid action: {action}")
    return _record(store, proposal_id, action, notes)


def _record(store, proposal_id: str, action: str, notes: str) -> dict:
    did = store.record_decision(proposal_id, action, notes)
    return {"id": did, "proposal_id": proposal_id, "action": action,
            "notes": notes, "recorded": True}


def activation_allowed(store, proposal_id: str) -> bool:
    """Read-only guard: has THIS proposal been explicitly approved (and not
    superseded by a later reject)? Later decisions win."""
    decisions = [d for d in store.list_decisions(200)
                 if d["proposal_id"] == proposal_id]
    if not decisions:
        return False
    latest = sorted(decisions, key=lambda d: d["decided_at"])[-1]
    return latest["action"] in ("approve", "edit")


def guard_activate(store, proposal_id: str) -> None:
    """Use before any plan activation. Raises when unapproved."""
    if not activation_allowed(store, proposal_id):
        raise PermissionError(
            "Plan activation blocked: no approved decision for this proposal. "
            "AI proposals never activate themselves.")
