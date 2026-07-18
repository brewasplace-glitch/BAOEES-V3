from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ENGINE_NAME = "Phoenix Project Graph"
ENGINE_VERSION = "v34.0"
ROOT = Path.cwd().resolve()
while not (ROOT / ".git").exists():
    if ROOT.parent == ROOT:
        raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")
    ROOT = ROOT.parent
OUTPUT_DIR = ROOT / "outputs/graph/v34_0"
POLICY_PATH = ROOT / "configs/phoenix/project_graph_policy_v34_0.json"
SCHEMA_PATH = ROOT / "configs/phoenix/project_graph_schema_v34_0.json"

@dataclass(frozen=True)
class GraphNode:
    object_id: str
    object_type: str
    name: str
    attributes: Dict[str, Any]
    revision: int
    fingerprint: str
    created_at: str
    updated_at: str

@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    attributes: Dict[str, Any]
    created_at: str

class PhoenixIdRegistry:
    PREFIXES = {
        "project": "PROJECT", "building": "BLD", "space": "SPC",
        "column": "COL", "beam": "BEAM", "foundation": "FND",
        "drawing": "DRW", "document": "DOC", "report": "RPT",
        "calculation": "CALC", "permit": "PRM", "cost_item": "COST",
        "schedule_item": "SCH", "geo_object": "GEO", "installation": "MEP",
    }
    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
    def create_id(self, object_type: str) -> str:
        key = object_type.strip().lower()
        prefix = self.PREFIXES.get(key, key.upper()[:8] or "OBJ")
        self._counters[key] = self._counters.get(key, 0) + 1
        return f"{prefix}-{self._counters[key]:06d}"

class PhoenixProjectGraph:
    ALLOWED_RELATIONS = {
        "contains", "belongs_to", "depends_on", "references", "located_in",
        "calculated_by", "generated_from", "requires", "updates", "affects",
        "validated_by", "scheduled_by", "costed_by",
    }
    def __init__(self) -> None:
        self.id_registry = PhoenixIdRegistry()
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._outgoing: Dict[str, Set[str]] = {}
        self._incoming: Dict[str, Set[str]] = {}
        self.graph_revision = 0
    @staticmethod
    def _fingerprint(data: Any) -> str:
        return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    def _require_node(self, object_id: str) -> GraphNode:
        if object_id not in self.nodes:
            raise KeyError(f"Onbekende node: {object_id}")
        return self.nodes[object_id]
    def add_node(self, object_type: str, name: str, attributes: Optional[Dict[str, Any]] = None, object_id: Optional[str] = None) -> GraphNode:
        node_id = object_id or self.id_registry.create_id(object_type)
        if node_id in self.nodes:
            raise ValueError(f"Node bestaat al: {node_id}")
        now = datetime.now().isoformat(timespec="seconds")
        payload = {"object_id": node_id, "object_type": object_type, "name": name, "attributes": attributes or {}, "revision": 1}
        node = GraphNode(node_id, object_type, name, attributes or {}, 1, self._fingerprint(payload), now, now)
        self.nodes[node_id] = node
        self._outgoing[node_id] = set()
        self._incoming[node_id] = set()
        self.graph_revision += 1
        return node
    def update_node(self, object_id: str, attributes: Dict[str, Any], name: Optional[str] = None) -> GraphNode:
        current = self._require_node(object_id)
        merged = dict(current.attributes)
        merged.update(attributes)
        revision = current.revision + 1
        now = datetime.now().isoformat(timespec="seconds")
        payload = {"object_id": object_id, "object_type": current.object_type, "name": name or current.name, "attributes": merged, "revision": revision}
        node = GraphNode(object_id, current.object_type, name or current.name, merged, revision, self._fingerprint(payload), current.created_at, now)
        self.nodes[object_id] = node
        self.graph_revision += 1
        return node
    def add_relation(self, source_id: str, target_id: str, relation_type: str, attributes: Optional[Dict[str, Any]] = None) -> GraphEdge:
        self._require_node(source_id); self._require_node(target_id)
        if relation_type not in self.ALLOWED_RELATIONS:
            raise ValueError(f"Niet-toegestane relatie: {relation_type}")
        edge_id = "EDGE-" + hashlib.sha256(f"{source_id}|{relation_type}|{target_id}".encode("utf-8")).hexdigest()[:16]
        if edge_id in self.edges:
            return self.edges[edge_id]
        edge = GraphEdge(edge_id, source_id, target_id, relation_type, attributes or {}, datetime.now().isoformat(timespec="seconds"))
        self.edges[edge_id] = edge
        self._outgoing[source_id].add(edge_id)
        self._incoming[target_id].add(edge_id)
        self.graph_revision += 1
        return edge
    def find_object(self, object_id: str) -> Optional[Dict[str, Any]]:
        node = self.nodes.get(object_id)
        return asdict(node) if node else None
    def find_children(self, object_id: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._require_node(object_id)
        result = []
        for edge_id in sorted(self._outgoing[object_id]):
            edge = self.edges[edge_id]
            if relation_type and edge.relation_type != relation_type:
                continue
            result.append(asdict(self.nodes[edge.target_id]))
        return result
    def find_parents(self, object_id: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._require_node(object_id)
        result = []
        for edge_id in sorted(self._incoming[object_id]):
            edge = self.edges[edge_id]
            if relation_type and edge.relation_type != relation_type:
                continue
            result.append(asdict(self.nodes[edge.source_id]))
        return result
    def find_dependencies(self, object_id: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        self._require_node(object_id)
        visited: Set[str] = {object_id}
        queue: List[Tuple[str, int]] = [(object_id, 0)]
        result: List[Dict[str, Any]] = []
        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for edge_id in sorted(self._outgoing[current_id]):
                edge = self.edges[edge_id]
                if edge.relation_type not in {"depends_on", "requires", "affects"} or edge.target_id in visited:
                    continue
                visited.add(edge.target_id)
                item = asdict(self.nodes[edge.target_id]); item["depth"] = depth + 1; item["via_relation"] = edge.relation_type
                result.append(item); queue.append((edge.target_id, depth + 1))
        return result
    def impact_analysis(self, object_id: str) -> Dict[str, Any]:
        self._require_node(object_id)
        visited: Set[str] = {object_id}
        queue: List[Tuple[str, int]] = [(object_id, 0)]
        impacts: List[Dict[str, Any]] = []
        while queue:
            current_id, depth = queue.pop(0)
            for edge_id in sorted(self._incoming[current_id]):
                edge = self.edges[edge_id]
                if edge.source_id in visited:
                    continue
                visited.add(edge.source_id)
                node = self.nodes[edge.source_id]
                impacts.append({"object_id": node.object_id, "object_type": node.object_type, "name": node.name, "depth": depth + 1, "relation_type": edge.relation_type})
                queue.append((edge.source_id, depth + 1))
        result = {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "changed_object": object_id, "impact_count": len(impacts), "impacts": impacts, "generated_at": datetime.now().isoformat(timespec="seconds")}
        self._write_json("impact_analysis.json", result)
        return result
    def validate(self) -> Dict[str, Any]:
        errors = []
        for edge in self.edges.values():
            if edge.source_id not in self.nodes: errors.append(f"Ontbrekende source node: {edge.source_id}")
            if edge.target_id not in self.nodes: errors.append(f"Ontbrekende target node: {edge.target_id}")
            if edge.relation_type not in self.ALLOWED_RELATIONS: errors.append(f"Ongeldige relatie: {edge.relation_type}")
        return {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "node_count": len(self.nodes), "edge_count": len(self.edges), "graph_revision": self.graph_revision, "errors": errors, "status": "PASS" if not errors else "FAIL"}
    def export(self) -> Dict[str, Any]:
        nodes = [asdict(n) for n in self.nodes.values()]
        relations = [asdict(e) for e in self.edges.values()]
        dependency_map = {node_id: [x["object_id"] for x in self.find_dependencies(node_id)] for node_id in self.nodes}
        graph = {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "graph_revision": self.graph_revision, "nodes": nodes, "relations": relations, "fingerprint": self._fingerprint({"nodes": nodes, "relations": relations}), "generated_at": datetime.now().isoformat(timespec="seconds")}
        self._write_json("graph.json", graph); self._write_json("nodes.json", nodes); self._write_json("relations.json", relations); self._write_json("dependency_map.json", dependency_map)
        self._write_json("graph_summary.json", {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "node_count": len(nodes), "edge_count": len(relations), "graph_revision": self.graph_revision, "status": self.validate()["status"], "generated_at": datetime.now().isoformat(timespec="seconds")})
        return graph
    def integration_test(self) -> Dict[str, Any]:
        graph = PhoenixProjectGraph()
        project = graph.add_node("project", "Project Phoenix v34 Test")
        building = graph.add_node("building", "Testgebouw")
        column = graph.add_node("column", "Kolom K12")
        foundation = graph.add_node("foundation", "Fundering F1")
        calculation = graph.add_node("calculation", "Constructieberekening")
        cost = graph.add_node("cost_item", "Kostenpost fundering")
        permit = graph.add_node("permit", "Omgevingsvergunning")
        graph.add_relation(project.object_id, building.object_id, "contains")
        graph.add_relation(building.object_id, column.object_id, "contains")
        graph.add_relation(column.object_id, foundation.object_id, "depends_on")
        graph.add_relation(calculation.object_id, column.object_id, "calculated_by")
        graph.add_relation(cost.object_id, foundation.object_id, "depends_on")
        graph.add_relation(permit.object_id, building.object_id, "requires")
        dependencies = graph.find_dependencies(column.object_id)
        impacts = graph.impact_analysis(foundation.object_id)
        checks = {"node_registry": len(graph.nodes) == 7, "edge_registry": len(graph.edges) == 6, "dependency_query": any(x["object_id"] == foundation.object_id for x in dependencies), "impact_analysis": any(x["object_id"] == column.object_id for x in impacts["impacts"]), "graph_validation": graph.validate()["status"] == "PASS", "graph_export": graph.export()["version"] == ENGINE_VERSION}
        result = {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL", "generated_at": datetime.now().isoformat(timespec="seconds")}
        self._write_json("project_graph_integration_test_v34_0.json", result)
        return result
    def _write_json(self, filename: str, data: Any) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    parser.add_argument("command", choices=["self-test", "integration-test", "demo"])
    args = parser.parse_args()
    graph = PhoenixProjectGraph()
    if args.command == "self-test":
        result = {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "policy_exists": POLICY_PATH.is_file(), "schema_exists": SCHEMA_PATH.is_file(), "status": "PASS" if POLICY_PATH.is_file() and SCHEMA_PATH.is_file() else "FAIL"}
    elif args.command == "integration-test":
        result = graph.integration_test()
    else:
        project = graph.add_node("project", "Project Phoenix Demo")
        building = graph.add_node("building", "Demo Gebouw")
        graph.add_relation(project.object_id, building.object_id, "contains")
        graph.export(); result = graph.validate()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS": raise SystemExit(1)

if __name__ == "__main__":
    main()
