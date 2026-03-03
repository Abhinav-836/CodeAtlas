"""
Advanced execution flow extraction with dependency analysis.
PRODUCTION-SAFE VERSION
"""

import ast
import builtins
import networkx as nx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# =========================
# DATA MODELS
# =========================

@dataclass
class FunctionCall:
    caller: str
    callee: str
    lineno: int
    module: Optional[str] = None
    args_count: int = 0
    is_method_call: bool = False
    is_builtin: bool = False


@dataclass
class ExecutionPath:
    source: str
    target: str
    calls: List[FunctionCall]
    depth: int
    is_cyclic: bool = False


# =========================
# FLOW EXTRACTOR
# =========================

class FlowExtractor:
    """Extracts execution flow and call graphs from code."""

    def __init__(self):
        self.call_graph = nx.DiGraph()
        self.functions: Dict[str, Dict[str, Any]] = {}

    # ---------- PUBLIC ----------
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        self.call_graph.clear()
        self.functions.clear()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            self._attach_parents(tree)
            self._extract_functions(tree, file_path)
            calls = self._extract_calls(tree, file_path)
            self._build_call_graph(calls)

            return {
                "file_path": file_path,
                "functions": list(self.functions.values()),
                "calls": [self._call_to_dict(c) for c in calls],
                "call_graph": self._graph_to_dict(),
                "execution_paths": [self._path_to_dict(p) for p in self._analyze_execution_paths()],
                "entry_points": self._find_entry_points(),
                "cycles": self._detect_cycles(),
                "metrics": self._calculate_metrics(),
            }

        except Exception as e:
            logger.exception("Flow analysis failed")
            return {"file_path": file_path, "error": str(e)}

    # ---------- AST PREP ----------
    def _attach_parents(self, tree: ast.AST):
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

    # ---------- FUNCTION EXTRACTION ----------
    def _extract_functions(self, tree: ast.AST, file_path: str):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = f"{file_path}:{node.name}"
                info = {
                    "name": node.name,
                    "qualified": name,
                    "lineno": node.lineno,
                    "type": "function",
                    "file": file_path,
                }
                self.functions[name] = info
                self.call_graph.add_node(name, **info)

            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        name = f"{file_path}:{node.name}.{item.name}"
                        info = {
                            "name": f"{node.name}.{item.name}",
                            "qualified": name,
                            "lineno": item.lineno,
                            "type": "method",
                            "class": node.name,
                            "file": file_path,
                        }
                        self.functions[name] = info
                        self.call_graph.add_node(name, **info)

    # ---------- CALL EXTRACTION ----------
    def _extract_calls(self, tree: ast.AST, file_path: str) -> List[FunctionCall]:
        calls: List[FunctionCall] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call = self._parse_call(node, file_path)
                if call:
                    calls.append(call)

        return calls

    def _parse_call(self, node: ast.Call, file_path: str) -> Optional[FunctionCall]:
        caller = self._get_caller(node, file_path)
        callee = self._get_callee(node.func)

        if not callee:
            return None

        return FunctionCall(
            caller=caller,
            callee=callee,
            lineno=node.lineno,
            args_count=len(node.args) + len(node.keywords),
            is_method_call=isinstance(node.func, ast.Attribute),
            is_builtin=hasattr(builtins, callee),
        )

    def _get_caller(self, node: ast.AST, file_path: str) -> str:
        parent = node
        while hasattr(parent, "parent"):
            parent = parent.parent
            if isinstance(parent, ast.FunctionDef):
                return f"{file_path}:{parent.name}"
            if isinstance(parent, ast.ClassDef):
                return f"{file_path}:{parent.name}"
        return f"{file_path}:<module>"

    def _get_callee(self, func: ast.AST) -> Optional[str]:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    # ---------- GRAPH ----------
    def _build_call_graph(self, calls: List[FunctionCall]):
        for call in calls:
            self.call_graph.add_node(call.caller)
            self.call_graph.add_node(call.callee)

            edge = self.call_graph.get_edge_data(call.caller, call.callee)
            if edge:
                edge["weight"] += 1
                edge["calls"].append(call)
            else:
                self.call_graph.add_edge(
                    call.caller,
                    call.callee,
                    weight=1,
                    calls=[call],
                )

    # ---------- ANALYSIS ----------
    def _analyze_execution_paths(self) -> List[ExecutionPath]:
        paths: List[ExecutionPath] = []

        sources = [n for n in self.call_graph.nodes if self.call_graph.in_degree(n) == 0]
        sinks = [n for n in self.call_graph.nodes if self.call_graph.out_degree(n) == 0]

        for src in sources[:3]:
            for tgt in sinks[:3]:
                try:
                    for path in nx.all_simple_paths(self.call_graph, src, tgt, cutoff=6):
                        paths.append(
                            ExecutionPath(
                                source=src,
                                target=tgt,
                                calls=self._calls_for_path(path),
                                depth=len(path) - 1,
                                is_cyclic=False,
                            )
                        )
                except nx.NetworkXNoPath:
                    continue

        return paths

    def _calls_for_path(self, path: List[str]) -> List[FunctionCall]:
        calls: List[FunctionCall] = []
        for i in range(len(path) - 1):
            data = self.call_graph.get_edge_data(path[i], path[i + 1])
            if data:
                calls.extend(data.get("calls", []))
        return calls

    # ---------- METRICS ----------
    def _find_entry_points(self) -> List[str]:
        return [n for n in self.call_graph.nodes if self.call_graph.in_degree(n) == 0]

    def _detect_cycles(self) -> List[List[str]]:
        return list(nx.simple_cycles(self.call_graph))

    def _calculate_metrics(self) -> Dict[str, Any]:
        if not self.call_graph.nodes:
            return {}

        return {
            "nodes": self.call_graph.number_of_nodes(),
            "edges": self.call_graph.number_of_edges(),
            "density": nx.density(self.call_graph),
            "is_dag": nx.is_directed_acyclic_graph(self.call_graph),
        }

    # ---------- SERIALIZATION ----------
    def _call_to_dict(self, c: FunctionCall) -> Dict[str, Any]:
        return vars(c)

    def _path_to_dict(self, p: ExecutionPath) -> Dict[str, Any]:
        return {
            "source": p.source,
            "target": p.target,
            "depth": p.depth,
            "calls": [self._call_to_dict(c) for c in p.calls],
        }

    def _graph_to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": list(self.call_graph.nodes),
            "edges": list(self.call_graph.edges(data=True)),
        }


# =========================
# CONVENIENCE
# =========================

def extract_execution_flow(file_path: str) -> Dict[str, Any]:
    return FlowExtractor().analyze_file(file_path)
