"""
Knowledge state builder for the normative evaluator.

Per Normative Admissibility Framework:
- GroundSet (G) is an evidential basis (KnowledgeNode set).
- Context (C) is "terms considered as given" and is NOT part of GroundSet.

This module builds GroundSet from tool results ONLY.

CRITICAL SECURITY INVARIANTS
---------------------------
1) Only externally verifiable observer tools may contribute to GroundSet.
2) Personalization/memory artifacts MUST NOT become KnowledgeNodes.
   (Otherwise: self-licensing / semantic laundering through the tool boundary.)

This builder:
- Does not interpret meaning
- Does not infer new knowledge
- Does not synthesize or summarize
- Only admits or rejects candidate knowledge atoms for normative use
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from ..logging import logger
from ..models.messages import ToolResultSpeechAct
from .models import KnowledgeNode, Scope, Source, Status

if TYPE_CHECKING:
    from ..citations import Ground


class KnowledgeStateBuilder:
    """
    Build knowledge state (GroundSet) from tool results.

    Mapping rule:
    - Tool call results → KnowledgeNode(scope=FACTUAL, source=OBSERVED, status=CONFIRMED, strength=strong)
    """

    def build(self, tool_results: list[ToolResultSpeechAct]) -> list[KnowledgeNode]:
        nodes, _ = self.build_with_references(tool_results)
        return nodes

    def build_with_references(
        self, tool_results: list[ToolResultSpeechAct]
    ) -> tuple[list[KnowledgeNode], dict[str, list[str]]]:
        """Build knowledge nodes and tool-call keyed reference mapping."""
        nodes: list[KnowledgeNode] = []
        tool_call_refs: dict[str, list[str]] = {}
        for result in tool_results:
            k = self._tool_result_to_knowledge(result)
            if not k:
                continue

            produced_nodes: list[KnowledgeNode] = k if isinstance(k, list) else [k]

            nodes.extend(produced_nodes)

            if result.tool_call_id:
                refs = [node.semantic_id or node.id for node in produced_nodes]
                if refs:
                    tool_call_refs[result.tool_call_id] = refs

        logger.debug(f"KnowledgeStateBuilder: Built {len(nodes)} knowledge nodes from tool results")
        return nodes, tool_call_refs

    def materialize_external_grounds(
        self,
        knowledge_nodes: list[KnowledgeNode],
        grounds: list[Ground],
    ) -> list[KnowledgeNode]:
        """Inject external grounds as factual observed nodes when missing."""
        if not grounds:
            return knowledge_nodes

        existing_ids = {node.id for node in knowledge_nodes}
        existing_semantic_ids = {node.semantic_id for node in knowledge_nodes if node.semantic_id}
        expanded = list(knowledge_nodes)

        for ground in grounds:
            if ground.ground_id in existing_ids or ground.ground_id in existing_semantic_ids:
                continue
            expanded.append(
                KnowledgeNode(
                    id=ground.ground_id,
                    source=Source.OBSERVED,
                    status=Status.CONFIRMED,
                    confidence=1.0,
                    scope=Scope.FACTUAL,
                    strength="strong",
                    semantic_id=ground.ground_id,
                )
            )

        return expanded

    def _tool_result_to_knowledge(
        self, tool_result: ToolResultSpeechAct
    ) -> KnowledgeNode | list[KnowledgeNode] | None:
        """
        Map tool call result to KnowledgeNode(s).

        IMPORTANT:
        - This assumes observer tools return externally verifiable facts.
        - It explicitly filters out non-epistemic tools (memory/personalization/state).
        - This module intentionally does not process Context (C).
        """
        tool_name = tool_result.tool_name or "unknown"
        if self._is_non_epistemic_tool(tool_name):
            logger.debug(f"Filtering non-epistemic tool result from GroundSet: {tool_name}")
            return None

        # NEW v0.3.1: Extract semantic_id(s) for LinkSet integration.
        result = self._extract_semantic_id(tool_result)

        # Array results (search_issues, search_transactions, etc.)
        if isinstance(result, list):
            nodes: list[KnowledgeNode] = []
            for idx, semantic_id in enumerate(result):
                stable = self._stable_id_fragment(f"{tool_name}:{semantic_id}")
                nodes.append(
                    KnowledgeNode(
                        id=f"tool_{tool_name}_item{idx}_{stable}",
                        source=Source.OBSERVED,
                        status=Status.CONFIRMED,
                        confidence=1.0,
                        scope=Scope.FACTUAL,
                        strength="strong",
                        semantic_id=semantic_id,
                    )
                )
            return nodes if nodes else None

        # Single result
        semantic_id = result
        tool_result_dump = (
            tool_result.model_dump() if hasattr(tool_result, "model_dump") else tool_result.dict()
        )
        stable = self._stable_id_fragment(
            json.dumps(
                {"tool": tool_name, "tool_result": tool_result_dump},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
        return KnowledgeNode(
            id=f"tool_{tool_name}_{stable}",
            source=Source.OBSERVED,
            status=Status.CONFIRMED,
            confidence=1.0,
            scope=Scope.FACTUAL,
            strength="strong",
            semantic_id=semantic_id,
        )

    @staticmethod
    def _is_non_epistemic_tool(tool_name: str) -> bool:
        """
        Best-effort guard: exclude tools that traffic in personalization/memory/state.

        This is intentionally conservative until tool definitions carry explicit
        epistemic typing (e.g., tool.epistemic_class = "observer"|"llm_proxy").
        """
        name = (tool_name or "").lower()

        # Legacy cognitive context tool
        if name == "get_user_cognitive_context":
            return True

        # Personalization / memory lifecycle tools (OpenAI cookbook-like patterns)
        if "personalization" in name or "personal_context" in name:
            return True

        if "memory" in name and any(
            k in name for k in ("save", "note", "notes", "load", "consolidat", "distill", "state")
        ):
            return True

        if "profile" in name and any(
            k in name for k in ("save", "set", "update", "load", "consolidat")
        ):
            return True

        # Extra catch-alls for "memory without saying memory"
        # (best-effort until explicit tool epistemic typing is available)
        return any(
            k in name for k in ("remember", "preference", "preferences", "setting", "settings")
        )

    def _extract_semantic_id(self, tool_result: ToolResultSpeechAct) -> str | list[str] | None:
        """
        Extract semantic ID(s) from tool result for LinkSet integration.

        Convention:
        - All entities have {entity_type}_id or {entity_type}_key field
        - Semantic ID = "{entity_type}_{value}"
        """
        content = tool_result.result_text
        if not content:
            return None

        try:
            data = json.loads(content) if isinstance(content, str) else content

            if isinstance(data, list):
                semantic_ids: list[str] = []
                for item in data:
                    if isinstance(item, dict):
                        entity_id = self._extract_entity_id(item)
                        if entity_id:
                            semantic_ids.append(entity_id)
                return semantic_ids if semantic_ids else None

            if isinstance(data, dict):
                return self._extract_entity_id(data)

            return None

        except (json.JSONDecodeError, TypeError, AttributeError):
            return None

    @staticmethod
    def _extract_entity_id(data: dict) -> str | None:
        """
        Extract primary entity ID from dict via convention.

        Priority order (first match wins):
        1. *_key fields
        2. *_id fields
        """
        import re

        key_pattern = re.compile(r"^(\w+)_key$")
        id_pattern = re.compile(r"^(\w+)_id$")

        for field_name, value in data.items():
            match = key_pattern.match(field_name)
            if match and value:
                return f"{match.group(1)}_{value}"

        for field_name, value in data.items():
            match = id_pattern.match(field_name)
            if match and value:
                return f"{match.group(1)}_{value}"

        return None

    @staticmethod
    def _stable_id_fragment(value: str) -> str:
        """
        Deterministic ID fragment.

        NOTE: Do NOT use Python's built-in hash() here because it is salted per process
        (PYTHONHASHSEED) and breaks determinism.
        """
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:10]
