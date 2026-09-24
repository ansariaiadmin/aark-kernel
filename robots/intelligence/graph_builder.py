import ast
from pathlib import Path
from typing import Dict, List, Set

class RepoIntelligence:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()

    def find_python_files(self) -> List[Path]:
        return [
            p for p in self.root_dir.rglob("*.py")
            if not any(part.startswith((".", "venv", "__pycache__")) for part in p.parts)
        ]

    def extract_imports(self, file_path: Path) -> Set[str]:
        imports = set()
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
        except Exception:
            pass
        return imports

    def generate_zero_token_stub(self, file_path: Path) -> str:
        """Strips function/method bodies, keeping signatures, types, and docstrings."""
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except Exception:
            return ""

        class StubTransformer(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                docstring = ast.get_docstring(node)
                new_body = []
                if docstring:
                    new_body.append(ast.Expr(value=ast.Constant(value=docstring)))
                new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                node.body = new_body
                return node

            def visit_AsyncFunctionDef(self, node):
                return self.visit_FunctionDef(node)

        stub_tree = StubTransformer().visit(tree)
        ast.fix_missing_locations(stub_tree)
        return ast.unparse(stub_tree)

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        graph = {}
        for file in self.find_python_files():
            rel_path = str(file.relative_to(self.root_dir))
            graph[rel_path] = sorted(list(self.extract_imports(file)))
        return graph

if __name__ == "__main__":
    import json
    intel = RepoIntelligence(".")
    graph = intel.build_dependency_graph()
    print(json.dumps({"total_files": len(graph), "graph": graph}, indent=2))
