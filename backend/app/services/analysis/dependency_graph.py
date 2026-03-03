"""
Advanced dependency graph analysis for codebases.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any

import networkx as nx

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies."""
    IMPORT = "import"
    FUNCTION_CALL = "function_call"
    CLASS_INHERITANCE = "class_inheritance"
    MODULE_REFERENCE = "module_reference"
    FILE_IMPORT = "file_import"
    EXTERNAL_LIBRARY = "external_library"


@dataclass
class Dependency:
    """Represents a dependency relationship."""
    source: str
    target: str
    type: DependencyType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyGraph:
    """Advanced dependency graph with analysis capabilities."""

    def __init__(self):
        self.graph = nx.DiGraph()

    # -------------------------
    # Graph Construction
    # -------------------------

    def add_dependency(self, dependency: Dependency):
        self.graph.add_node(dependency.source)
        self.graph.add_node(dependency.target)

        if self.graph.has_edge(dependency.source, dependency.target):
            edge = self.graph[dependency.source][dependency.target]
            edge["weight"] += dependency.weight
            edge["types"].add(dependency.type.value)
            edge["dependencies"].append(dependency)
        else:
            self.graph.add_edge(
                dependency.source,
                dependency.target,
                weight=dependency.weight,
                types={dependency.type.value},
                dependencies=[dependency],
            )

    def analyze_imports(self, file_path: str, imports: List[Dict[str, Any]]):
        file_name = Path(file_path).stem

        for imp in imports:
            module = imp.get("module", "")
            for name in imp.get("names", []):
                self.add_dependency(
                    Dependency(
                        source=file_name,
                        target=f"{module}.{name}" if module else name,
                        type=DependencyType.IMPORT,
                        metadata={
                            "module": module,
                            "name": name,
                            "lineno": imp.get("lineno"),
                            "is_from_import": imp.get("is_from_import", False),
                        },
                    )
                )

    def analyze_function_calls(self, file_path: str, calls: List[Dict[str, Any]]):
        file_name = Path(file_path).stem

        for call in calls:
            if "caller" in call and "callee" in call:
                self.add_dependency(
                    Dependency(
                        source=f"{file_name}.{call['caller']}",
                        target=call["callee"],
                        type=DependencyType.FUNCTION_CALL,
                        metadata={
                            "lineno": call.get("lineno"),
                            "args_count": call.get("args_count", 0),
                            "is_method_call": call.get("is_method_call", False),
                        },
                    )
                )

    def analyze_class_hierarchy(self, file_path: str, classes: List[Dict[str, Any]]):
        file_name = Path(file_path).stem

        for cls in classes:
            class_name = f"{file_name}.{cls['name']}"
            for base in cls.get("bases", []):
                self.add_dependency(
                    Dependency(
                        source=class_name,
                        target=base,
                        type=DependencyType.CLASS_INHERITANCE,
                        metadata={
                            "class_name": cls["name"],
                            "base_class": base,
                            "lineno": cls.get("lineno"),
                        },
                    )
                )

    # -------------------------
    # Analysis
    # -------------------------

    def find_circular_dependencies(self) -> List[List[str]]:
        try:
            return list(nx.simple_cycles(self.graph))
        except Exception as e:
            logger.error("Cycle detection failed: %s", e)
            return []

    def calculate_metrics(self) -> Dict[str, Any]:
        if self.graph.number_of_nodes() == 0:
            return {}

        in_degrees = dict(self.graph.in_degree())
        out_degrees = dict(self.graph.out_degree())

        metrics = {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "is_dag": nx.is_directed_acyclic_graph(self.graph),
            "max_in_degree": max(in_degrees.values(), default=0),
            "max_out_degree": max(out_degrees.values(), default=0),
            "avg_in_degree": sum(in_degrees.values()) / max(len(in_degrees), 1),
            "avg_out_degree": sum(out_degrees.values()) / max(len(out_degrees), 1),
            "strongly_connected_components": nx.number_strongly_connected_components(self.graph),
            "weakly_connected_components": nx.number_weakly_connected_components(self.graph),
        }

        try:
            centrality = nx.betweenness_centrality(self.graph)
            metrics["most_central_nodes"] = sorted(
                centrality.items(), key=lambda x: x[1], reverse=True
            )[:5]
        except Exception as e:
            logger.debug("Centrality failed: %s", e)

        return metrics

    def suggest_refactoring(self) -> List[Dict[str, Any]]:
        suggestions = []
        in_deg = dict(self.graph.in_degree())
        out_deg = dict(self.graph.out_degree())

        avg_in = sum(in_deg.values()) / max(len(in_deg), 1)
        avg_out = sum(out_deg.values()) / max(len(out_deg), 1)

        for node, d in in_deg.items():
            if d > avg_in * 3:
                suggestions.append({
                    "type": "high_coupling",
                    "node": node,
                    "priority": "high",
                    "reason": f"{d} incoming dependencies",
                })

        for node, d in out_deg.items():
            if d > avg_out * 3:
                suggestions.append({
                    "type": "high_fanout",
                    "node": node,
                    "priority": "medium",
                    "reason": f"{d} outgoing dependencies",
                })

        for cycle in self.find_circular_dependencies()[:5]:
            suggestions.append({
                "type": "circular_dependency",
                "cycle": cycle,
                "priority": "high",
            })

        return suggestions

    # -------------------------
    # Export / Visualization
    # -------------------------

    def visualize_as_dot(self) -> str:
        lines = [
            'digraph G {',
            '  rankdir="LR";',
            '  node [shape="box"];'
        ]

        for node in self.graph.nodes():
            lines.append(f'  "{node}";')

        for src, tgt, data in self.graph.edges(data=True):
            label = f'x{data.get("weight", 1)}' if data.get("weight", 1) > 1 else ""
            lines.append(
                f'  "{src}" -> "{tgt}" [label="{label}"];'
            )

        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": list(self.graph.nodes()),
            "edges": [
                {
                    "source": s,
                    "target": t,
                    "weight": d.get("weight", 1),
                    "types": list(d.get("types", [])),
                }
                for s, t, d in self.graph.edges(data=True)
            ],
            "metrics": self.calculate_metrics(),
        }

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> "DependencyGraph":
        graph = cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for edge in data.get("edges", []):
            graph.add_dependency(
                Dependency(
                    source=edge["source"],
                    target=edge["target"],
                    type=DependencyType.MODULE_REFERENCE,
                    weight=edge.get("weight", 1),
                )
            )
        return graph


# -------------------------
# Public API
# -------------------------

def build_dependency_graph(analysis_data: List[Dict[str, Any]]) -> DependencyGraph:
    graph = DependencyGraph()

    for file_data in analysis_data:
        if "imports" in file_data:
            graph.analyze_imports(file_data.get("file_path", ""), file_data["imports"])
        if "calls" in file_data:
            graph.analyze_function_calls(file_data.get("file_path", ""), file_data["calls"])
        if "classes" in file_data:
            graph.analyze_class_hierarchy(file_data.get("file_path", ""), file_data["classes"])

    return graph


def analyze_dependencies(analysis_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    graph = build_dependency_graph(analysis_data)
    return {
        "graph": graph.to_dict(),
        "circular_dependencies": graph.find_circular_dependencies(),
        "metrics": graph.calculate_metrics(),
        "refactoring_suggestions": graph.suggest_refactoring(),
        "dot": graph.visualize_as_dot(),
    }
