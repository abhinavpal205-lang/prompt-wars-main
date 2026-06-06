"""Tests for confidence-aware weighted fusion."""

import pytest

from app.schemas import Modality, SignalResult
from app.services.fusion import FusionOutput, NoUsableSignalsError, fuse


def signal(
    modality: Modality,
    distress: float,
    confidence: float,
    *,
    crisis: bool = False,
) -> SignalResult:
    return SignalResult(
        modality=modality,
        distress_0_100=distress,
        confidence_0_1=confidence,
        crisis_flag=crisis,
    )


def test_form_only_passes_through() -> None:
    """In form mode the form is the only signal: effective weight 1.0."""
    out = fuse([signal("form", 62.5, 1.0)])
    assert out.composite_0_100 == pytest.approx(62.5)
    assert out.band == "elevated"
    assert [s.modality for s in out.used] == ["form"]


def test_weighted_mean_uses_priors_and_confidence() -> None:
    """weight = prior * confidence; composite is the weighted mean."""
    out = fuse(
        [
            signal("form", 80.0, 1.0),  # weight 0.60
            signal("transcript", 20.0, 0.5),  # weight 0.10
        ]
    )
    expected = (0.60 * 80.0 + 0.10 * 20.0) / 0.70
    assert out.composite_0_100 == pytest.approx(expected)


def test_zero_confidence_signals_are_dropped_and_weights_renormalized() -> None:
    out = fuse(
        [
            signal("transcript", 60.0, 1.0),
            signal("audio", 100.0, 0.0),  # failed provider: must not move the score
            signal("facial", 100.0, 0.0),
        ]
    )
    assert out.composite_0_100 == pytest.approx(60.0)
    assert [s.modality for s in out.used] == ["transcript"]


def test_low_confidence_soft_cue_barely_nudges_the_form() -> None:
    """Honesty about signals: facial frames cannot overrule the self-report."""
    out = fuse(
        [
            signal("form", 10.0, 1.0),  # weight 0.60
            signal("facial", 90.0, 0.3),  # weight 0.03
        ]
    )
    assert out.composite_0_100 == pytest.approx((0.60 * 10.0 + 0.03 * 90.0) / 0.63)
    assert out.band == "calm"


def test_all_modalities_combine() -> None:
    out = fuse(
        [
            signal("form", 50.0, 1.0),
            signal("transcript", 70.0, 1.0),
            signal("audio", 30.0, 1.0),
            signal("facial", 40.0, 1.0),
        ]
    )
    expected = (0.6 * 50 + 0.2 * 70 + 0.1 * 30 + 0.1 * 40) / 1.0
    assert out.composite_0_100 == pytest.approx(expected)


def test_no_usable_signals_raises() -> None:
    with pytest.raises(NoUsableSignalsError):
        fuse([signal("audio", 50.0, 0.0)])
    with pytest.raises(NoUsableSignalsError):
        fuse([])


def test_crisis_flag_propagates_even_from_dropped_signal() -> None:
    """A crisis flag must survive even if the signal's score is unusable."""
    out = fuse(
        [
            signal("form", 5.0, 1.0),
            signal("transcript", 0.0, 0.0, crisis=True),
        ]
    )
    assert out.crisis is True
    assert out.band == "calm"


def test_no_crisis_when_no_flags() -> None:
    assert fuse([signal("form", 90.0, 1.0)]).crisis is False


def test_output_is_banded_at_threshold() -> None:
    out: FusionOutput = fuse([signal("form", 75.0, 1.0)])
    assert out.band == "high"
