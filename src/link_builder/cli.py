"""
CLI for LinkBuilder - generates StatementGroundLinks from run artifacts.

Per FORMAL_SPEC_v0.3.md §3 Epistemic Firewall.

Usage:
    python -m src.link_builder.cli <run_file.json>

Output:
    file.json → file.links.json (replaces .json suffix)

CRITICAL WORKFLOW:
------------------
1. Offline mode (this CLI):
   - Run artifacts → LinkBuilder → .links.json
   - Evaluator consumes .links.json separately

2. Pipeline mode (future):
   - Agent output → LinkBuilder → Evaluator (same process)
   - Links passed directly, not via file

This CLI implements offline mode for post-hoc analysis.

v0.3.0 LIMITATION:
------------------
Links generated but NOT integrated with evaluator yet.

ID mismatch problem:
- LinkMatcher creates: ground_id = f"tool_get_issue_{hash}"
- KnowledgeStateBuilder creates: id = f"tool_{tool_name}_{hash}"
- Hash computation may differ → IDs don't match

v0.3.1 FIX required:
- KnowledgeStateBuilder adds semantic_id field
- OR LinkMatcher uses same hash algorithm
- OR evaluator accepts both ID formats

Current output is VALID links structure, but unusable by evaluator.
"""

import sys
from pathlib import Path
from loguru import logger

from .service import LinkBuilderService


def main():
    """
    Generate StatementGroundLinks from run artifacts.
    
    Usage:
        python -m src.link_builder.cli <run_file.json>
    
    Output:
        run_file.links.json (replaces .json with .links.json)
    """
    # Parse arguments
    if len(sys.argv) < 2:
        logger.error("Usage: python -m src.link_builder.cli <run_file.json>")
        logger.error("Example: python -m src.link_builder.cli results/run_trial0.json")
        sys.exit(1)
    
    run_file = Path(sys.argv[1])
    
    # Validate input
    if not run_file.exists():
        logger.error(f"Run file not found: {run_file}")
        sys.exit(1)
    
    if not run_file.suffix == '.json':
        logger.error(f"Expected .json file, got: {run_file.suffix}")
        sys.exit(1)
    
    logger.info(f"LinkBuilder CLI: Processing {run_file}")
    
    # Initialize service
    service = LinkBuilderService()
    
    # Load run data
    try:
        run_data = service.load_run(str(run_file))
    except Exception as e:
        logger.error(f"Failed to load run file: {e}")
        sys.exit(1)
    
    # Build links
    try:
        link_set = service.build_links(run_data)
    except Exception as e:
        logger.error(f"Failed to build links: {e}")
        sys.exit(1)
    
    # Save links
    # CRITICAL: Replace .json with .links.json (not append)
    # file.json → file.links.json (not file.json.links.json)
    output_file = run_file.with_suffix('.links.json')
    try:
        service.save_links(link_set, str(output_file))
    except Exception as e:
        logger.error(f"Failed to save links: {e}")
        sys.exit(1)
    
    # Print summary
    logger.info(f"✓ Generated {len(link_set.links)} links")
    logger.info(f"✓ Output: {output_file}")
    
    # Role distribution
    role_counts = {}
    for link in link_set.links:
        role_counts[link.role] = role_counts.get(link.role, 0) + 1
    
    logger.info(f"  Role distribution: {dict(role_counts)}")
    
    # Creator distribution
    creator_counts = {}
    for link in link_set.links:
        creator_counts[link.provenance.creator] = creator_counts.get(link.provenance.creator, 0) + 1
    
    logger.info(f"  Creator distribution: {dict(creator_counts)}")
    
    # Warn about ID mismatch (v0.3.0 known issue)
    logger.warning(
        "v0.3.0 LIMITATION: Links use heuristic ground_id that may not match evaluator's "
        "KnowledgeNode IDs. Integration with evaluator requires v0.3.1 ID sync fix."
    )


if __name__ == "__main__":
    main()
