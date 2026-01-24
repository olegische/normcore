import json

from evaluator.models.messages import ToolResultSpeechAct
from evaluator.normative.knowledge_builder import KnowledgeStateBuilder
from evaluator.normative.models import Scope, Source, Status


def _tool_result(tool_name: str, result_text: str) -> ToolResultSpeechAct:
    return ToolResultSpeechAct(tool_name=tool_name, result_text=result_text)


def test_non_epistemic_tool_is_filtered():
    builder = KnowledgeStateBuilder()
    result = _tool_result("save_memory", "{\"foo\": \"bar\"}")
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
    payload = json.dumps([
        {"task_key": "T-1"},
        {"task_key": "T-2"},
    ])
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
        _tool_result("search_tasks", json.dumps([{ "task_key": "T-1" }]))
    ]
    nodes = builder.build(results)
    assert len(nodes) == 2


def test_stable_id_fragment_is_deterministic():
    builder = KnowledgeStateBuilder()
    value = "same-input"
    assert builder._stable_id_fragment(value) == builder._stable_id_fragment(value)
