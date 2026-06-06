"""Exhaustive tests for deterministic form scoring and banding."""

import pytest

from app import constants
from app.schemas import Band, FormResponse
from app.services.form_scorer import band_for, derive_triggers, score_form


def ideal_answers() -> list[int]:
    """Answers reporting no strain: 0 on negative items, 4 on reversed ones."""
    return [4 if i in constants.REVERSE_ITEM_INDICES else 0 for i in range(10)]


def worst_answers() -> list[int]:
    """Answers reporting maximum strain on every item."""
    return [0 if i in constants.REVERSE_ITEM_INDICES else 4 for i in range(10)]


@pytest.mark.parametrize(
    ("composite", "expected"),
    [
        (0.0, "calm"),
        (24.9, "calm"),
        (25.0, "mild"),
        (49.9, "mild"),
        (50.0, "elevated"),
        (74.9, "elevated"),
        (75.0, "high"),
        (100.0, "high"),
    ],
)
def test_band_boundaries(composite: float, expected: Band) -> None:
    assert band_for(composite) == expected


def test_ideal_answers_score_zero_and_calm() -> None:
    score = score_form(FormResponse(answers=ideal_answers()))
    assert score.composite_0_100 == 0.0
    assert score.band == "calm"
    assert score.crisis is False
    assert score.triggers == []


def test_worst_answers_score_hundred_and_high() -> None:
    score = score_form(FormResponse(answers=worst_answers()))
    assert score.composite_0_100 == 100.0
    assert score.band == "high"


def test_all_zero_answers_are_not_calm() -> None:
    """All-zero answers mean 'never relaxed/confident/hopeful' on reversed items."""
    score = score_form(FormResponse(answers=[0] * 10))
    expected = len(constants.REVERSE_ITEM_INDICES) * constants.LIKERT_MAX / 40 * 100
    assert score.composite_0_100 == pytest.approx(expected)
    assert score.band == "mild"


def test_midpoint_raw_normalizes_to_fifty() -> None:
    score = score_form(FormResponse(answers=[2] * 10))
    assert score.composite_0_100 == pytest.approx(50.0)
    assert score.band == "elevated"


def test_reverse_items_are_reverse_scored() -> None:
    """A 4 on a positively-worded item must contribute zero strain."""
    answers = ideal_answers()
    reverse_index = next(iter(constants.REVERSE_ITEM_INDICES))
    answers[reverse_index] = 0  # "never able to take breaks"
    score = score_form(FormResponse(answers=answers))
    assert score.composite_0_100 == pytest.approx(10.0)


def test_safety_flag_forces_crisis_even_when_calm() -> None:
    score = score_form(FormResponse(answers=ideal_answers(), safety_flag=True))
    assert score.band == "calm"
    assert score.crisis is True


def test_safety_flag_false_means_no_crisis_even_when_high() -> None:
    score = score_form(FormResponse(answers=worst_answers(), safety_flag=False))
    assert score.crisis is False


@pytest.mark.parametrize("index", sorted(constants.TRIGGER_BY_ITEM))
def test_each_item_maps_to_its_trigger(index: int) -> None:
    answers = ideal_answers()
    answers[index] = 0 if index in constants.REVERSE_ITEM_INDICES else 4
    assert derive_triggers(answers) == [constants.TRIGGER_BY_ITEM[index]]


def test_trigger_threshold_requires_notable_strain() -> None:
    """Strain of 2 of 4 is not flagged; 3 of 4 is."""
    answers = ideal_answers()
    answers[1] = 2
    assert derive_triggers(answers) == []
    answers[1] = 3
    assert derive_triggers(answers) == ["sleep"]
