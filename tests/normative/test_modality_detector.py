
from normcore.normative.modality_detector import ModalityDetector
from normcore.normative.models import Modality, Statement


def test_refusal_has_highest_priority():
    detector = ModalityDetector()
    text = "I don't know if this is better, please provide more info."
    assert detector.detect(text) == Modality.REFUSAL


def test_first_person_would_not_is_refusal():
    detector = ModalityDetector()
    text = "I would not publish to PyPI yet because there is a blocker."
    assert detector.detect(text) == Modality.REFUSAL


def test_goal_conditional_over_recommendation():
    detector = ModalityDetector()
    text = "If your goal is speed, X is better."
    assert detector.detect(text) == Modality.CONDITIONAL


def test_personalization_conditional_over_recommendation():
    detector = ModalityDetector()
    text = "X is better for you."
    assert detector.detect(text) == Modality.CONDITIONAL


def test_recommendation_in_core_over_tail_conditional():
    detector = ModalityDetector()
    text = "X is better. If you want more detail, I can explain."
    assert detector.detect(text) == Modality.ASSERTIVE


def test_conditional_detected_in_core():
    detector = ModalityDetector()
    text = "If you want speed, choose X."
    assert detector.detect(text) == Modality.CONDITIONAL


def test_descriptive_detected():
    detector = ModalityDetector()
    text = "Task A blocks Task B."
    assert detector.detect(text) == Modality.DESCRIPTIVE


def test_default_assertive_when_no_indicators():
    detector = ModalityDetector()
    text = "Proceed with task A tomorrow."
    assert detector.detect(text) == Modality.ASSERTIVE


def test_detect_with_conditions_extracts_conditions_for_conditional():
    detector = ModalityDetector()
    statement = Statement(
        id="s1", subject="agent", predicate="participation", raw_text="If X, do Y unless Z."
    )
    detector.detect_with_conditions(statement)
    assert statement.modality == Modality.CONDITIONAL
    assert "x" in " ".join(statement.conditions).lower()
    assert any("not" in c.lower() for c in statement.conditions)


def test_detect_with_conditions_does_not_extract_for_assertive_tail_if():
    detector = ModalityDetector()
    statement = Statement(
        id="s2",
        subject="agent",
        predicate="participation",
        raw_text="X is better. If you want more, ask.",
    )
    detector.detect_with_conditions(statement)
    assert statement.modality == Modality.ASSERTIVE
    assert statement.conditions == []
