"""Shared fixtures for local store tests."""

import os
import shutil
from pathlib import Path

import pytest

from tools.local_store.catalog import Catalog
from tools.local_store.graph_store import GraphStore
from tools.local_store.store import LocalStore


@pytest.fixture
def catalog(tmp_path):
    """Fresh SQLite catalog for each test."""
    db_path = tmp_path / "test_catalog.db"
    cat = Catalog(db_path=db_path)
    yield cat
    cat.close()


@pytest.fixture
def graph_store(tmp_path):
    """Fresh LadybugDB graph store for each test."""
    db_path = tmp_path / "test_graph.db"
    store = GraphStore(db_path=db_path)
    yield store
    store.close()


@pytest.fixture
def local_store(tmp_path):
    """Fresh integrated LocalStore for each test."""
    store = LocalStore(cache_dir=tmp_path / "cache")
    yield store
    store.close()


def make_minimal_cx2():
    """Create a minimal CX2 network: 2 nodes, 1 edge."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "Test Minimal Network",
        "description": "A minimal test network",
        "ndex-workflow": "test",
    })
    cx2.add_node(node_id=0, attributes={"name": "ProteinA", "type": "protein"})
    cx2.add_node(node_id=1, attributes={"name": "ProteinB", "type": "protein"})
    cx2.add_edge(
        edge_id=0,
        source=0,
        target=1,
        attributes={"interaction": "increases", "evidence": "PMID:12345"},
    )
    return cx2


def make_second_bel_cx2():
    """Create a second BEL network with some overlapping proteins and contradictions."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "NS1 Immune Evasion BEL",
        "description": "BEL network for NS1 immune evasion mechanisms",
        "ndex-workflow": "tier3_analysis",
    })
    nodes = [
        (0, {"name": "NS1", "type": "protein", "function": "p"}),
        (1, {"name": "TRIM25", "type": "protein", "function": "p"}),
        (2, {"name": "RIG-I", "type": "protein", "function": "p"}),
        (3, {"name": "MAVS", "type": "protein", "function": "p"}),
        (4, {"name": "IRF3", "type": "protein", "function": "p"}),
    ]
    edges = [
        # Contradiction with first network: here NS1 *increases* TRIM25 (first says decreases)
        (0, 0, 1, {"interaction": "increases", "evidence": "NS1 stabilizes TRIM25 under certain conditions"}),
        (1, 1, 2, {"interaction": "directlyIncreases", "evidence": "TRIM25 activates RIG-I"}),
        (2, 2, 3, {"interaction": "increases", "evidence": "RIG-I signals through MAVS"}),
        (3, 3, 4, {"interaction": "increases", "evidence": "MAVS activates IRF3"}),
        (4, 0, 3, {"interaction": "decreases", "evidence": "NS1 disrupts MAVS signaling"}),
    ]
    for nid, attrs in nodes:
        cx2.add_node(node_id=nid, attributes=attrs)
    for eid, src, tgt, attrs in edges:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes=attrs)
    return cx2


def make_plans_cx2():
    """Create a plans self-knowledge network."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "ndexagent drh plans",
        "description": "Research plans for agent drh",
        "ndex-workflow": "plans",
        "ndex-agent": "drh",
    })
    # Mission -> Goals -> Actions hierarchy
    nodes = [
        (0, {"name": "IAV Host-Pathogen Research", "type": "mission", "state": "active"}),
        (1, {"name": "Map TRIM25 interactions", "type": "goal", "state": "active", "priority": "high"}),
        (2, {"name": "Survey NS1 mechanisms", "type": "goal", "state": "active", "priority": "medium"}),
        (3, {"name": "Search TRIM25 literature", "type": "action", "state": "completed", "depends_on": ""}),
        (4, {"name": "Extract TRIM25 BEL network", "type": "action", "state": "in_progress", "depends_on": "3"}),
        (5, {"name": "Validate TRIM25 interactions", "type": "action", "state": "planned", "depends_on": "4"}),
        (6, {"name": "Search NS1 evasion papers", "type": "action", "state": "planned", "depends_on": ""}),
        (7, {"name": "Cross-reference with Krogan data", "type": "action", "state": "planned", "depends_on": "4,6"}),
    ]
    edges = [
        (0, 0, 1, {"interaction": "has_goal"}),
        (1, 0, 2, {"interaction": "has_goal"}),
        (2, 1, 3, {"interaction": "has_action"}),
        (3, 1, 4, {"interaction": "has_action"}),
        (4, 1, 5, {"interaction": "has_action"}),
        (5, 2, 6, {"interaction": "has_action"}),
        (6, 2, 7, {"interaction": "has_action"}),
    ]
    for nid, attrs in nodes:
        cx2.add_node(node_id=nid, attributes=attrs)
    for eid, src, tgt, attrs in edges:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes=attrs)
    return cx2


def make_episodic_cx2():
    """Create an episodic memory self-knowledge network."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "ndexagent drh episodic memory",
        "description": "Session history for agent drh",
        "ndex-workflow": "episodic_memory",
        "ndex-agent": "drh",
    })
    nodes = [
        (0, {"name": "Session 2026-03-12 14:00", "type": "session",
             "timestamp": "2026-03-12T14:00:00Z",
             "actions_taken": "Initial setup, scanned bioRxiv for IAV papers"}),
        (1, {"name": "Session 2026-03-13 09:00", "type": "session",
             "timestamp": "2026-03-13T09:00:00Z",
             "actions_taken": "Reviewed TRIM25 paper PMID:38001234, extracted BEL network"}),
        (2, {"name": "Session 2026-03-14 11:00", "type": "session",
             "timestamp": "2026-03-14T11:00:00Z",
             "actions_taken": "Published TRIM25 analysis to NDEx, began NS1 review"}),
        (3, {"name": "Session 2026-03-15 10:00", "type": "session",
             "timestamp": "2026-03-15T10:00:00Z",
             "actions_taken": "Completed NS1 evasion review, found contradiction with TRIM25 paper"}),
    ]
    edges = [
        (0, 0, 1, {"interaction": "followed_by"}),
        (1, 1, 2, {"interaction": "followed_by"}),
        (2, 2, 3, {"interaction": "followed_by"}),
    ]
    for nid, attrs in nodes:
        cx2.add_node(node_id=nid, attributes=attrs)
    for eid, src, tgt, attrs in edges:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes=attrs)
    return cx2


def make_collaborator_cx2():
    """Create a collaborator map self-knowledge network."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "ndexagent drh collaborator map",
        "description": "Known agents and collaborators for drh",
        "ndex-workflow": "collaborator_map",
        "ndex-agent": "drh",
    })
    nodes = [
        (0, {"name": "drh", "type": "agent", "role": "research_synthesizer",
             "expertise": "host-pathogen interactions, knowledge integration"}),
        (1, {"name": "rdaneel", "type": "agent", "role": "literature_reviewer",
             "expertise": "bioRxiv scanning, paper triage, BEL extraction"}),
        (2, {"name": "janetexample", "type": "agent", "role": "literature_reviewer",
             "expertise": "ubiquitin biology, innate immunity, critical analysis"}),
        (3, {"name": "Dexter Pratt", "type": "human", "role": "platform_developer",
             "expertise": "NDEx, network biology, systems architecture"}),
        (4, {"name": "Pratibha", "type": "human", "role": "experimentalist",
             "expertise": "IAV experiments, host-pathogen assays"}),
    ]
    edges = [
        (0, 0, 1, {"interaction": "collaborates_with", "context": "paper triage and review"}),
        (1, 0, 2, {"interaction": "collaborates_with", "context": "critical analysis of findings"}),
        (2, 0, 3, {"interaction": "reports_to", "context": "project oversight"}),
        (3, 0, 4, {"interaction": "collaborates_with", "context": "hypothesis testing"}),
        (4, 1, 2, {"interaction": "collaborates_with", "context": "cross-review of analyses"}),
    ]
    for nid, attrs in nodes:
        cx2.add_node(node_id=nid, attributes=attrs)
    for eid, src, tgt, attrs in edges:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes=attrs)
    return cx2


def make_bel_cx2():
    """Create a BEL-style knowledge graph CX2 network."""
    from ndex2.cx2 import CX2Network

    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": "TRIM25 BEL Analysis",
        "description": "BEL network for TRIM25/RdRp interactions",
        "ndex-workflow": "tier3_analysis",
    })
    nodes = [
        (0, {"name": "TRIM25", "type": "protein", "function": "p"}),
        (1, {"name": "RIG-I", "type": "protein", "function": "p"}),
        (2, {"name": "NS1", "type": "protein", "function": "p"}),
        (3, {"name": "IFNB1", "type": "rna", "function": "r"}),
        (4, {"name": "ISG15", "type": "protein", "function": "p"}),
    ]
    edges = [
        (0, 0, 1, {"interaction": "directlyIncreases", "evidence": "TRIM25 ubiquitinates RIG-I CARD domains"}),
        (1, 2, 0, {"interaction": "directlyDecreases", "evidence": "NS1 binds TRIM25 coiled-coil domain"}),
        (2, 1, 3, {"interaction": "increases", "evidence": "RIG-I activates IFN-beta transcription"}),
        (3, 3, 4, {"interaction": "increases", "evidence": "IFN-beta induces ISG15 expression"}),
        (4, 2, 1, {"interaction": "decreases", "evidence": "NS1 sequesters RIG-I"}),
    ]
    for nid, attrs in nodes:
        cx2.add_node(node_id=nid, attributes=attrs)
    for eid, src, tgt, attrs in edges:
        cx2.add_edge(edge_id=eid, source=src, target=tgt, attributes=attrs)
    return cx2
