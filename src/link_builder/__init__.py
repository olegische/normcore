"""
LinkBuilder - StatementGroundLinks generation and validation.

Per FORMAL_SPEC_v0.3.md §2-3 StatementGroundLinks and Epistemic Firewall.

Public API:
- LinkBuilderService: Main service (validates and creates links)
- LinkMatcher: Structural heuristics for candidate links
- StatementGroundLink, LinkSet: Data models
- LinkRole, CreatorType, EvidenceType: Enums

Usage (offline mode):
```python
from src.link_builder import LinkBuilderService

service = LinkBuilderService()
run_data = service.load_run("results/run.json")
link_set = service.build_links(run_data)
service.save_links(link_set, "results/run.json.links.json")
```

Usage (pipeline mode - future):
```python
from src.link_builder import LinkBuilderService

service = LinkBuilderService()
link_set = service.build_links(run_data)
# Pass link_set to evaluator
```

CRITICAL v0.3.0 LIMITATION:
---------------------------
Links NOT integrated with evaluator yet (ID mismatch problem).

See service.py module docstring for details.
"""

from .service import LinkBuilderService
from .link_matcher import LinkMatcher
from .models import (
    StatementGroundLink,
    LinkSet,
    LinkRole,
    CreatorType,
    EvidenceType,
    Provenance,
)

__all__ = [
    "LinkBuilderService",
    "LinkMatcher",
    "StatementGroundLink",
    "LinkSet",
    "LinkRole",
    "CreatorType",
    "EvidenceType",
    "Provenance",
]

