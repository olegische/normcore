from pydantic import ValidationError

from evaluator.models import (
    AdmissibilityJudgment,
    AdmissibilityStatus,
    AssistantSpeechAct,
    EvaluationResult,
    GroundRef,
    LinkRole,
    LinkSet,
    Provenance,
    StatementEvaluation,
    StatementGroundLink,
    TextSpeechAct,
)
from evaluator.models.links import CreatorType, EvidenceType
from evaluator.models.messages import ToolResultSpeechAct, _TextPart


def test_public_model_roundtrip():
    ref = GroundRef(
        id="k1",
        scope="factual",
        source="observed",
        status="confirmed",
        confidence=1.0,
        strength="strong",
    )
    evaluation = StatementEvaluation(
        statement_id="s1",
        statement="X",
        modality="assertive",
        license={"assertive"},
        status=AdmissibilityStatus.ACCEPTABLE,
        grounding_trace=[ref],
    )
    judgment = AdmissibilityJudgment(
        status=AdmissibilityStatus.ACCEPTABLE,
        licensed=True,
        can_retry=False,
        statement_evaluations=[evaluation],
    )
    assert judgment.status == AdmissibilityStatus.ACCEPTABLE


def test_tool_result_speech_act_defaults():
    act = ToolResultSpeechAct(tool_name="tool", result_text="ok")
    assert act.arguments == {}


def test_text_part_forbids_extra_fields():
    try:
        _TextPart(type="text", text="hi", extra="nope")
    except ValidationError:
        assert True
    else:
        assert False, "Expected ValidationError for extra fields"


def test_links_models_defaults():
    provenance = Provenance(
        creator=CreatorType.HUMAN,
        evidence_type=EvidenceType.EXPLICIT,
    )
    link = StatementGroundLink(
        statement_id="s1",
        ground_id="g1",
        role=LinkRole.SUPPORTS,
        provenance=provenance,
    )
    link_set = LinkSet(links=[link])
    assert link_set.links[0].role == LinkRole.SUPPORTS


def test_models_init_exports():
    # __all__ paths are wired by importing from evaluator.models
    assert isinstance(TextSpeechAct(text="x"), AssistantSpeechAct.__args__)
