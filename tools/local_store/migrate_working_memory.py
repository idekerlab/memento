"""Migrate agent working_memory.md to local graph store + NDEx.

This script:
1. Caches rdaneel's existing NDEx networks into the local store
2. Creates a session history (episodic memory) network from scan logs
3. Creates a paper tracking network from the papers-read table

Run with: python -m tools.local_store.migrate_working_memory [--dry-run]
"""

import argparse
import sys
import time

from ndex2.cx2 import CX2Network

from tools.ndex_mcp.config import load_ndex_config, has_credentials
from tools.ndex_mcp.ndex_client_wrapper import NDExClientWrapper
from tools.local_store.store import LocalStore


# UUIDs from working_memory.md scan h (2026-03-12)
KNOWN_NETWORKS = [
    # Scan h networks
    ("80212c0f-1e3a-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-12", "tier1"),
    ("13bbe281-1e3b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review TenVIP-seq IAV RdRP pausing", "tier2"),
    ("21b0baf3-1e3b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review DDX3X IFN-beta translation", "tier2"),
    ("3064ebc5-1e3b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review arenavirus aberrant genomes RIG-I", "tier2"),
    ("e9cbd797-1e3b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-analysis TenVIP-seq TRIM25 RdRp pausing", "tier3"),
    ("f9678239-1e3b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-highlight TenVIP-seq TRIM25 RdRp", "tier3"),
    # Scan backlog (2026-03-10 through 2026-03-11)
    ("ba963865-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-10", "tier1"),
    ("bab02907-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review c-Fos/M2", "tier2"),
    ("bac314c9-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review ncISG15", "tier2"),
    ("baddc8bb-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review PA-X dual roles", "tier2"),
    ("baf8077d-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-analysis c-Fos/M2", "tier3"),
    ("bb39f283-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-highlight c-Fos/M2", "tier3"),
    ("bb104a6f-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-analysis ncISG15", "tier3"),
    ("bb520e65-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-highlight ncISG15", "tier3"),
    ("bb23ab61-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-analysis PA-X", "tier3"),
    ("bb698e07-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-highlight PA-X", "tier3"),
    ("bb7dd959-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-11", "tier1"),
    ("bb983f2b-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review Host RBP Network", "tier2"),
    ("bbaf70ad-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-11 supplementary", "tier1"),
    ("bbc8c50f-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-review H5N1 neuroinvasion cats", "tier2"),
    ("bbda2a31-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-11 (scan c)", "tier1"),
    ("bbf3a5a3-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-11 (scan d)", "tier1"),
    ("bc061c35-1e2b-11f1-94e8-005056ae3c32", "ndexagent biorxiv-daily-scan 2026-03-11 (scan e)", "tier1"),
    # Demo collaborator networks
    ("7522f9b6-1ff9-11f1-94e8-005056ae3c32", "Critique by janetexample", "demo"),
    ("845449ca-1ff9-11f1-94e8-005056ae3c32", "Synthesis by drh", "demo"),
    ("847fc69e-1ff9-11f1-94e8-005056ae3c32", "Plans by drh", "demo"),
    ("8498f3f2-1ff9-11f1-94e8-005056ae3c32", "Episodic memory by drh", "demo"),
    ("84b1fa36-1ff9-11f1-94e8-005056ae3c32", "Collaborator map by drh", "demo"),
]


def _infer_category(name: str, tier: str) -> str:
    """Infer catalog category from network name and tier."""
    if "plans" in name.lower():
        return "plan"
    if "episodic" in name.lower():
        return "episodic-memory"
    if "collaborator" in name.lower():
        return "collaborator-map"
    if tier == "tier1":
        return "review-log"
    if tier in ("tier2", "tier3"):
        return "science-kg"
    return "science-kg"


def cache_ndex_networks(store: LocalStore, ndex: NDExClientWrapper, dry_run: bool = False):
    """Download and cache rdaneel's known NDEx networks."""
    print(f"\n=== Caching {len(KNOWN_NETWORKS)} known networks ===\n")

    cached = 0
    errors = 0
    for uuid, name, tier in KNOWN_NETWORKS:
        category = _infer_category(name, tier)
        print(f"  [{tier}] {name[:50]}...", end=" ", flush=True)

        if dry_run:
            print("(dry run)")
            continue

        try:
            dl = ndex.download_network(uuid)
            if dl["status"] != "success":
                print(f"SKIP ({dl.get('message', 'download failed')[:40]})")
                errors += 1
                continue

            cx2 = CX2Network()
            cx2.create_from_raw_cx2(dl["data"])
            stats = store.import_network(cx2, uuid, agent="rdaneel", category=category)

            # Get NDEx timestamp and mark as published
            summary = ndex.get_network_summary(uuid)
            if summary["status"] == "success":
                ndex_mod = str(summary["data"].get("modificationTime", ""))
                store.mark_published(uuid, ndex_modified=ndex_mod)

            print(f"OK ({stats['node_count']}n, {stats['edge_count']}e)")
            cached += 1
            time.sleep(0.3)  # Be gentle with NDEx API
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

    print(f"\nCached: {cached}, Errors: {errors}")
    return cached


def build_session_history(store: LocalStore, dry_run: bool = False):
    """Build an episodic memory network from the scan log data."""
    print("\n=== Building session history network ===\n")

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "ndexagent rdaneel session history",
        "description": "Episodic memory: bioRxiv triage scan sessions for agent rdaneel",
        "ndex-workflow": "episodic_memory",
        "ndex-agent": "rdaneel",
    })

    sessions = [
        (0, {
            "name": "Scan 2026-03-10 (scan a)",
            "type": "session",
            "timestamp": "2026-03-10T00:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "8",
            "papers_tier2": "3",
            "papers_tier3": "3",
            "networks_published": "0",
            "key_findings": "c-Fos/M2 stabilization, ncISG15 restricts IAV, PA-X dual immune roles",
        }),
        (1, {
            "name": "Scan 2026-03-11 (scan b)",
            "type": "session",
            "timestamp": "2026-03-11T00:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "8",
            "papers_tier2": "1",
            "papers_tier3": "1",
            "networks_published": "0",
            "key_findings": "Host RBP Network: ~700 RBPs recruited by incoming IAV genome, GMPS/TOP2A/SRRM2/SPEN proviral",
        }),
        (2, {
            "name": "Scan 2026-03-11 supplementary",
            "type": "session",
            "timestamp": "2026-03-11T06:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "6",
            "papers_tier2": "1",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "H5N1 neuroinvasion in cats, B3.13 vs D1.1 genotype-dependent transmission",
        }),
        (3, {
            "name": "Scan 2026-03-11 (scan c)",
            "type": "session",
            "timestamp": "2026-03-11T12:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "0",
            "papers_tier2": "0",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "No new papers. Flagged IFIT3 RNA-binding and in-cell protein contact sites papers",
        }),
        (4, {
            "name": "Scan 2026-03-11 (scan d)",
            "type": "session",
            "timestamp": "2026-03-11T18:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "0",
            "papers_tier2": "0",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "2 older papers found: in virio RNA structure, IFN heterogeneity. IFIT3 published in J Virol",
        }),
        (5, {
            "name": "Scan 2026-03-11 (scan e)",
            "type": "session",
            "timestamp": "2026-03-11T23:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "0",
            "papers_tier2": "0",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "4 H5N1/dairy papers found outside window. Publication lull confirmed",
        }),
        (6, {
            "name": "Scan 2026-03-12 (scan f)",
            "type": "session",
            "timestamp": "2026-03-12T00:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "0",
            "papers_tier2": "0",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "H5N1 dry cow pathogenesis paper. 6-day publication lull",
        }),
        (7, {
            "name": "Scan 2026-03-12 (scan g)",
            "type": "session",
            "timestamp": "2026-03-12T06:00:00Z",
            "scan_method": "web search fallback",
            "papers_tier1": "0",
            "papers_tier2": "0",
            "papers_tier3": "0",
            "networks_published": "0",
            "key_findings": "No new papers. Web search coverage approaching saturation",
        }),
        (8, {
            "name": "Scan 2026-03-12 (scan h)",
            "type": "session",
            "timestamp": "2026-03-12T12:00:00Z",
            "scan_method": "bioRxiv MCP API (first successful)",
            "papers_tier1": "13",
            "papers_tier2": "3",
            "papers_tier3": "1",
            "networks_published": "6",
            "key_findings": "TRIM25 dual role: RIG-I ubiquitination + RdRp pausing. DDX3X IFN-beta translation. Arenavirus NVGs activate RIG-I. First successful API-based triage",
        }),
    ]

    for node_id, attrs in sessions:
        cx2.add_node(node_id=node_id, attributes=attrs)

    # Chain sessions with followed_by edges
    for i in range(len(sessions) - 1):
        cx2.add_edge(edge_id=i, source=i, target=i + 1, attributes={
            "interaction": "followed_by",
        })

    session_uuid = "rdaneel-session-history"

    if dry_run:
        print(f"  Would create session history: {len(sessions)} sessions, {len(sessions)-1} edges")
        return

    stats = store.import_network(cx2, session_uuid, agent="rdaneel", category="episodic-memory")
    print(f"  Created: {stats['node_count']} sessions, {stats['edge_count']} edges")
    return cx2


def build_paper_tracker(store: LocalStore, dry_run: bool = False):
    """Build a paper tracking network from the papers-read data."""
    print("\n=== Building paper tracker network ===\n")

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "ndexagent rdaneel papers read",
        "description": "Papers read and analyzed by agent rdaneel",
        "ndex-workflow": "paper_tracker",
        "ndex-agent": "rdaneel",
    })

    papers = [
        (0, {"name": "c-Fos/M2 stabilization", "type": "paper",
             "doi": "10.64898/2026.03.05.709812", "tier": "3",
             "key_claims": "c-Fos binds M2, prevents degradation, positive feedback via calcium"}),
        (1, {"name": "ncISG15 restricts IAV", "type": "paper",
             "doi": "10.64898/2026.01.15.699784", "tier": "3",
             "key_claims": "Novel ISG15 isoform inhibits polymerase, resists NS1"}),
        (2, {"name": "PA-X dual immune roles", "type": "paper",
             "doi": "10.64898/2026.01.30.702929", "tier": "3",
             "key_claims": "IFN-lambda suppression, MHC I disruption, bystander ISG suppression"}),
        (3, {"name": "Host RBP Network (VIR-CLASP)", "type": "paper",
             "doi": "10.64898/2025.12.10.693272", "tier": "3",
             "key_claims": "~700 RBPs recruited by incoming vRNA; GMPS, TOP2A, SRRM2, SPEN proviral"}),
        (4, {"name": "TenVIP-seq TRIM25/RdRp pausing", "type": "paper",
             "doi": "10.1101/2025.01.08.631631", "tier": "3",
             "key_claims": "TRIM25 KO reduces RdRp pausing globally; TRIM25 dual role: RIG-I ubiquitination + polymerase pausing"}),
        (5, {"name": "DDX3X IFN-beta translation", "type": "paper",
             "doi": "10.64898/2026.03.08.707086", "tier": "2",
             "key_claims": "DDX3X binds IFNB1 5-UTR directly; promotes IFN-beta translation"}),
        (6, {"name": "Arenavirus NVGs activate RIG-I", "type": "paper",
             "doi": "10.64898/2026.03.09.710519", "tier": "2",
             "key_claims": "NVGs activate RIG-I; Old World arenaviruses suppress NVG production to evade sensing"}),
    ]

    # Shared protein nodes for cross-referencing
    proteins = [
        (100, {"name": "TRIM25", "type": "protein"}),
        (101, {"name": "RIG-I", "type": "protein"}),
        (102, {"name": "NS1", "type": "protein"}),
        (103, {"name": "M2", "type": "protein"}),
        (104, {"name": "c-Fos", "type": "protein"}),
        (105, {"name": "ISG15", "type": "protein"}),
        (106, {"name": "PA-X", "type": "protein"}),
        (107, {"name": "DDX3X", "type": "protein"}),
        (108, {"name": "SRRM2", "type": "protein"}),
        (109, {"name": "TOP2A", "type": "protein"}),
        (110, {"name": "GMPS", "type": "protein"}),
    ]

    for nid, attrs in papers + proteins:
        cx2.add_node(node_id=nid, attributes=attrs)

    # Paper-to-protein "mentions" edges
    mentions = [
        (0, 0, 103, "mentions"),  # c-Fos/M2 -> M2
        (1, 0, 104, "mentions"),  # c-Fos/M2 -> c-Fos
        (2, 1, 105, "mentions"),  # ncISG15 -> ISG15
        (3, 1, 102, "mentions"),  # ncISG15 -> NS1
        (4, 2, 106, "mentions"),  # PA-X -> PA-X
        (5, 3, 108, "mentions"),  # RBP Network -> SRRM2
        (6, 3, 109, "mentions"),  # RBP Network -> TOP2A
        (7, 3, 110, "mentions"),  # RBP Network -> GMPS
        (8, 4, 100, "mentions"),  # TenVIP-seq -> TRIM25
        (9, 4, 101, "mentions"),  # TenVIP-seq -> RIG-I
        (10, 4, 102, "mentions"),  # TenVIP-seq -> NS1
        (11, 5, 107, "mentions"),  # DDX3X paper -> DDX3X
        (12, 6, 101, "mentions"),  # Arenavirus -> RIG-I
    ]

    # Cross-paper connections (discovered in working memory notes)
    connections = [
        (13, 3, 0, "cross_reference"),   # RBP Network <-> c-Fos/M2 (SRRM2 splices M segment)
        (14, 4, 6, "cross_reference"),   # TenVIP-seq <-> Arenavirus (RdRp pausing ↔ NVG generation)
    ]

    for eid, src, tgt, interaction in mentions + connections:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes={
            "interaction": interaction,
        })

    tracker_uuid = "rdaneel-papers-read"

    if dry_run:
        print(f"  Would create paper tracker: {len(papers)} papers, {len(proteins)} proteins, {len(mentions)+len(connections)} edges")
        return

    stats = store.import_network(cx2, tracker_uuid, agent="rdaneel", category="science-kg")
    print(f"  Created: {stats['node_count']} nodes, {stats['edge_count']} edges")
    return cx2


def main():
    parser = argparse.ArgumentParser(description="Migrate working_memory.md to local store")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--skip-cache", action="store_true", help="Skip NDEx network caching")
    parser.add_argument("--profile", default="rdaneel", help="NDEx profile")
    args = parser.parse_args()

    store = LocalStore()
    print(f"Local store: {store.cache_dir}")

    ndex = None
    if not args.skip_cache:
        try:
            config = load_ndex_config(profile=args.profile)
            if has_credentials(config):
                ndex = NDExClientWrapper(config)
                print(f"NDEx: {config.username}@{config.server}")
        except (ValueError, FileNotFoundError):
            print("NDEx credentials not available, skipping network caching")

    # Step 1: Cache existing NDEx networks
    if ndex and not args.skip_cache:
        cache_ndex_networks(store, ndex, dry_run=args.dry_run)

    # Step 2: Build session history
    build_session_history(store, dry_run=args.dry_run)

    # Step 3: Build paper tracker
    build_paper_tracker(store, dry_run=args.dry_run)

    if not args.dry_run:
        # Summary
        all_networks = store.query_catalog()
        print(f"\n=== Migration complete ===")
        print(f"Total cached networks: {len(all_networks)}")
        by_cat = {}
        for n in all_networks:
            cat = n.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat}: {count}")

    store.close()


if __name__ == "__main__":
    main()
