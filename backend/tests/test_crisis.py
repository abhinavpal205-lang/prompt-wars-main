"""Tests for crisis detection — must be high-recall and never score-gated."""

import pytest

from app.services.crisis import assess_crisis, crisis_resources, detect_crisis_text


@pytest.mark.parametrize(
    "text",
    [
        "sometimes I just want to end my life",
        "I have been thinking about suicide",
        "I'm SUICIDAL and scared",
        "i want to hurt myself again",
        "thinking of self harm",
        "I might cut myself",
        "honestly I wish I was dead",
        "there is no reason to live anymore",
        "main marna chahta hoon",
        "mujhe lagta hai jeena nahi chahti",
    ],
)
def test_detects_crisis_language(text: str) -> None:
    assert detect_crisis_text(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "I'm so stressed about my NEET results",
        "this mock test killed my confidence",
        "I feel dead tired after physics",
        "my life feels hectic before boards",
        "",
        None,
    ],
)
def test_does_not_flag_ordinary_exam_stress(text: str | None) -> None:
    assert detect_crisis_text(text) is False


def test_assess_crisis_safety_flag_alone() -> None:
    assert assess_crisis(safety_flag=True) is True


def test_assess_crisis_from_any_text() -> None:
    assert assess_crisis(texts=["all good", "I want to die"]) is True


def test_assess_crisis_from_signal_flags() -> None:
    assert assess_crisis(signal_flags=[False, True]) is True


def test_assess_crisis_all_clear() -> None:
    assert assess_crisis(safety_flag=False, texts=["fine", None], signal_flags=[False]) is False


def test_resources_include_tele_manas_numbers() -> None:
    resources = crisis_resources()
    assert "14416" in resources.phone_numbers
    assert "1-800-891-4416" in resources.phone_numbers
    assert "Tele-MANAS" in resources.helpline_name
