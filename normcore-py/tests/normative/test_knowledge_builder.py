import json

from normcore.models.messages import ToolResultSpeechAct
from normcore.normative.knowledge_builder import KnowledgeStateBuilder
from normcore.normative.models import Scope, Source, Status


def _tool_result(tool_name: str, result_text: str) -> ToolResultSpeechAct:
    return ToolResultSpeechAct(tool_name=tool_name, result_text=result_text)


def test_non_epistemic_tool_is_filtered():
    builder = KnowledgeStateBuilder()
    result = _tool_result("save_memory", '{"foo": "bar"}')
    assert builder._tool_result_to_knowledge(result) is None


def test_extract_semantic_id_single_dict():
    builder = KnowledgeStateBuilder()
    payload = json.dumps({"issue_id": "123"})
    result = _tool_result("get_issue", payload)
    node = builder._tool_result_to_knowledge(result)
    assert node is not None
    assert node.semantic_id == "issue_123"
    assert node.scope == Scope.FACTUAL
    assert node.source == Source.OBSERVED
    assert node.status == Status.CONFIRMED


def test_extract_semantic_id_list_creates_multiple_nodes():
    builder = KnowledgeStateBuilder()
    payload = json.dumps(
        [
            {"task_key": "T-1"},
            {"task_key": "T-2"},
        ]
    )
    result = _tool_result("search_tasks", payload)
    nodes = builder._tool_result_to_knowledge(result)
    assert isinstance(nodes, list)
    assert len(nodes) == 2
    assert nodes[0].semantic_id == "task_T-1"
    assert nodes[1].semantic_id == "task_T-2"


def test_build_skips_none_and_flattens_lists():
    builder = KnowledgeStateBuilder()
    results = [
        _tool_result("save_memory", "{}"),
        _tool_result("get_issue", json.dumps({"issue_id": "123"})),
        _tool_result("search_tasks", json.dumps([{"task_key": "T-1"}])),
    ]
    nodes = builder.build(results)
    assert len(nodes) == 2


def test_stable_id_fragment_is_deterministic():
    builder = KnowledgeStateBuilder()
    value = "same-input"
    assert builder._stable_id_fragment(value) == builder._stable_id_fragment(value)


def test_non_epistemic_tool_detection_extra_patterns():
    builder = KnowledgeStateBuilder()
    assert builder._is_non_epistemic_tool("get_user_cognitive_context")
    assert builder._is_non_epistemic_tool("load_personalization_profile")
    assert builder._is_non_epistemic_tool("save_memory_note")
    assert builder._is_non_epistemic_tool("update_profile_settings")
    assert builder._is_non_epistemic_tool("remember_this")


def test_extract_semantic_id_handles_empty_invalid_and_non_object_payloads():
    builder = KnowledgeStateBuilder()
    assert builder._extract_semantic_id(_tool_result("get_issue", "")) is None
    assert builder._extract_semantic_id(_tool_result("get_issue", "123")) is None
    assert builder._extract_semantic_id(_tool_result("get_issue", "{bad json}")) is None


def test_extract_entity_id_returns_none_when_no_matching_fields():
    builder = KnowledgeStateBuilder()
    assert builder._extract_entity_id({"foo": "bar"}) is None
