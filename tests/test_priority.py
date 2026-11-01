"""Tests for the deterministic priority scorer."""
from datetime import date, timedelta

import pytest

from core.priority import compute_priority_score


def base(**over):
    params = dict(impact=3, effort=3, priority_band="medium",
                  due_date=date.today(), today=date.today())
    params.update(over)
    return compute_priority_score(**params)


def test_deterministic_same_inputs_same_score():
    assert base() == base()
    assert base(today=date(2026, 1, 1), due_date=date(2026, 1, 1)) == \
           compute_priority_score(impact=3, effort=3, priority_band="medium",
                                  due_date=date.today().replace(2026, 1, 1), today=date(2026, 1, 1))


def test_higher_impact_raises_score():
    assert base(impact=4) > base(impact=3)


def test_higher_effort_lowers_score():
    assert base(effort=4) < base(effort=3)


def test_high_band_beats_low_band():
    assert base(priority_band="high") > base(priority_band="low")


def test_due_today_outranks_due_next_week():
    assert base(due_date=date.today() + timedelta(days=0)) > \
           base(due_date=date.today() + timedelta(days=7))


def test_overdue_ticks_up_urgency_consciously():
    overdue = base(due_date=date.today() - timedelta(days=3))
    today_t = base(due_date=date.today())
    assert overdue == today_t          # both capped at 5.5 - honest stop, not runaway


def test_no_due_date_scores_neutral_urgency():
    assert base(due_date=None) == base(due_date=date.today()) - 5.5


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        base(impact=9)
    with pytest.raises(ValueError):
        base(priority_band="urgent")
