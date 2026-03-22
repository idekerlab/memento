"""T5: Agent Self-Knowledge Operations.

Test the specific patterns agents use to manage their own state:
plans, episodic memory, collaborator maps.
"""

import pytest

from tools.local_store.cx2_import import import_cx2_network
from tools.local_store.cx2_export import export_cx2_network
from tools.local_store.graph_store import _clean_map
from tests.local_store.conftest import make_plans_cx2, make_episodic_cx2, make_collaborator_cx2


class TestT5Plans:
    """T5.1: Plans network operations."""

    @pytest.fixture(autouse=True)
    def setup_plans(self, graph_store):
        self.graph = graph_store
        self.uuid = "plans-drh"
        cx2 = make_plans_cx2()
        import_cx2_network(graph_store, cx2, self.uuid)

    def test_find_planned_actions(self):
        """Find all actions with state = 'planned'."""
        rows = self.graph.execute(
            "MATCH (n:BioNode {network_uuid: $uuid}) "
            "WHERE n.node_type = 'action' "
            "RETURN n.name, n.properties",
            {"uuid": self.uuid},
        )
        planned = [r for r in rows if _clean_map(r[1]).get("state") == "planned"]
        assert len(planned) == 3
        planned_names = sorted(r[0] for r in planned)
        assert "Validate TRIM25 interactions" in planned_names
        assert "Search NS1 evasion papers" in planned_names
        assert "Cross-reference with Krogan data" in planned_names

    def test_mission_goal_action_hierarchy(self):
        """Traverse mission -> goal -> action hierarchy."""
        rows = self.graph.execute(
            "MATCH (m:BioNode {node_type: 'mission'})"
            "-[g:Interacts {interaction: 'has_goal'}]->(goal:BioNode)"
            "-[a:Interacts {interaction: 'has_action'}]->(action:BioNode) "
            "WHERE m.network_uuid = $uuid "
            "RETURN m.name, goal.name, action.name",
            {"uuid": self.uuid},
        )
        assert len(rows) == 5  # 5 actions total across 2 goals
        # Verify structure
        missions = {r[0] for r in rows}
        assert missions == {"IAV Host-Pathogen Research"}

    def test_update_action_state(self):
        """Change an action's state from 'planned' to 'in_progress'."""
        # Find the "Search NS1 evasion papers" action
        rows = self.graph.execute(
            "MATCH (n:BioNode {name: 'Search NS1 evasion papers'}) RETURN n.properties"
        )
        props = _clean_map(rows[0][0])
        assert props["state"] == "planned"

        # Update state
        self.graph.execute(
            "MATCH (n:BioNode {name: 'Search NS1 evasion papers'}) "
            "SET n.properties = map(['state', 'depends_on'], ['in_progress', ''])"
        )

        rows = self.graph.execute(
            "MATCH (n:BioNode {name: 'Search NS1 evasion papers'}) RETURN n.properties"
        )
        assert rows[0][0]["state"] == "in_progress"

    def test_add_action_and_export(self):
        """Add a new action node, link it, export to CX2."""
        # Add new action
        self.graph.add_node(
            node_id=100,
            network_uuid=self.uuid,
            name="Analyze RIPLET redundancy",
            node_type="action",
            properties={"state": "planned", "depends_on": "5"},
        )
        self.graph.add_edge(
            src_id=1,  # "Map TRIM25 interactions" goal
            tgt_id=100,
            edge_id=100,
            network_uuid=self.uuid,
            interaction="has_action",
        )
        self.graph.link_node_to_network(100, self.uuid)

        # Export and verify
        exported = export_cx2_network(self.graph, self.uuid)
        nodes = exported.get_nodes()
        assert len(nodes) == 9  # 8 original + 1 new
        new_nodes = [n for n in nodes.values() if n["v"].get("name") == "Analyze RIPLET redundancy"]
        assert len(new_nodes) == 1


class TestT5EpisodicMemory:
    """T5.2: Episodic memory operations."""

    @pytest.fixture(autouse=True)
    def setup_episodic(self, graph_store):
        self.graph = graph_store
        self.uuid = "episodic-drh"
        cx2 = make_episodic_cx2()
        import_cx2_network(graph_store, cx2, self.uuid)

    def test_find_most_recent_session(self):
        """Find the session with the latest timestamp."""
        rows = self.graph.execute(
            "MATCH (n:BioNode {network_uuid: $uuid, node_type: 'session'}) "
            "RETURN n.name, n.properties",
            {"uuid": self.uuid},
        )
        # Find most recent by timestamp in Python (MAP columns can't be sorted in Cypher)
        sessions = [(r[0], _clean_map(r[1])) for r in rows]
        most_recent = max(sessions, key=lambda s: s[1].get("timestamp", ""))
        assert "2026-03-15" in most_recent[1]["timestamp"]

    def test_find_session_by_topic(self):
        """Find session where TRIM25 paper was first mentioned."""
        rows = self.graph.execute(
            "MATCH (n:BioNode {network_uuid: $uuid, node_type: 'session'}) "
            "RETURN n.name, n.properties",
            {"uuid": self.uuid},
        )
        trim25_sessions = [
            r[0] for r in rows
            if "TRIM25" in _clean_map(r[1]).get("actions_taken", "")
        ]
        assert len(trim25_sessions) >= 1
        # First mention should be session 2
        assert "2026-03-13" in trim25_sessions[0]

    def test_add_session_and_export(self):
        """Add a new session, link with followed_by edge."""
        self.graph.add_node(
            node_id=100,
            network_uuid=self.uuid,
            name="Session 2026-03-16 09:00",
            node_type="session",
            properties={
                "timestamp": "2026-03-16T09:00:00Z",
                "actions_taken": "Implemented local graph store, ran tests",
            },
        )
        self.graph.add_edge(
            src_id=3,  # Previous last session
            tgt_id=100,
            edge_id=100,
            network_uuid=self.uuid,
            interaction="followed_by",
        )
        self.graph.link_node_to_network(100, self.uuid)

        # Export and verify chain
        exported = export_cx2_network(self.graph, self.uuid)
        nodes = exported.get_nodes()
        assert len(nodes) == 5  # 4 original + 1 new
        edges = exported.get_edges()
        assert len(edges) == 4  # 3 original + 1 new


class TestT5CollaboratorMap:
    """T5.3: Collaborator map operations."""

    @pytest.fixture(autouse=True)
    def setup_collaborators(self, graph_store):
        self.graph = graph_store
        self.uuid = "collabs-drh"
        cx2 = make_collaborator_cx2()
        import_cx2_network(graph_store, cx2, self.uuid)

    def test_find_by_role(self):
        """Find all agents with role = 'literature_reviewer'."""
        rows = self.graph.execute(
            "MATCH (n:BioNode {network_uuid: $uuid}) "
            "RETURN n.name, n.properties",
            {"uuid": self.uuid},
        )
        reviewers = [
            r[0] for r in rows
            if _clean_map(r[1]).get("role") == "literature_reviewer"
        ]
        assert sorted(reviewers) == ["janetexample", "rdaneel"]

    def test_find_by_expertise(self):
        """Find collaborators with expertise containing 'ubiquitin'."""
        rows = self.graph.execute(
            "MATCH (n:BioNode {network_uuid: $uuid}) "
            "RETURN n.name, n.properties",
            {"uuid": self.uuid},
        )
        ubiquitin_experts = [
            r[0] for r in rows
            if "ubiquitin" in _clean_map(r[1]).get("expertise", "")
        ]
        assert "janetexample" in ubiquitin_experts

    def test_add_collaborator_and_export(self):
        """Add a new agent and collaborates_with edge."""
        self.graph.add_node(
            node_id=100,
            network_uuid=self.uuid,
            name="Clara",
            node_type="human",
            properties={"role": "experimentalist", "expertise": "proteomics, mass spectrometry"},
        )
        self.graph.add_edge(
            src_id=0,  # drh
            tgt_id=100,
            edge_id=100,
            network_uuid=self.uuid,
            interaction="collaborates_with",
            properties={"context": "proteomics data analysis"},
        )
        self.graph.link_node_to_network(100, self.uuid)

        exported = export_cx2_network(self.graph, self.uuid)
        nodes = exported.get_nodes()
        assert len(nodes) == 6  # 5 original + 1 new
        clara_nodes = [n for n in nodes.values() if n["v"].get("name") == "Clara"]
        assert len(clara_nodes) == 1
        assert clara_nodes[0]["v"]["expertise"] == "proteomics, mass spectrometry"
