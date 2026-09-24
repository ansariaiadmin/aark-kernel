import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from robots.intelligence.graph_builder import RepoIntelligence

class ContextOptimizer:
    def __init__(self, root_dir: str = "."): 
        self.root_dir = Path(root_dir).resolve()
        self.intel = RepoIntelligence(self.root_dir)

    def minify_code(self, code_str: str) -> str:
        out = []
        for line in code_str.splitlines():
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            out.append(line)
        return "\n".join(out)

    def generate_optimized_context(self, critical_files: List[str], aggressive: bool = True) -> Dict[str, Any]:
        all_py_files = self.intel.find_python_files()
        critical_paths = {Path(self.root_dir / f).resolve() for f in critical_files}
        full_files_payload = []
        stub_files_payload = []
        orig_len = 0
        opt_len = 0

        for f in all_py_files:
            rel = str(f.relative_to(self.root_dir))
            content = f.read_text(encoding="utf-8")
            orig_len += len(content)
            if f in critical_paths:
                c = self.minify_code(content) if aggressive else content
                full_files_payload.append({"path": rel, "content": c})
                opt_len += len(c)
            else:
                stub = self.intel.generate_zero_token_stub(f)
                if aggressive:
                    stub = self.minify_code(stub)
                if stub.strip():
                    stub_files_payload.append({"path": rel, "stubs": stub})
                    opt_len += len(stub)

        savings = (1 - (opt_len / max(1, orig_len))) * 100
        return {
            "critical_files": full_files_payload,
            "interface_stubs": stub_files_payload,
            "metrics": {
                "original_chars": orig_len,
                "optimized_chars": opt_len,
                "compression_ratio": f"{savings:.2f}%"
            }
        }

if __name__ == "__main__":
    opt = ContextOptimizer(".")
    res = opt.generate_optimized_context(["backend/app/main.py"], aggressive=True)
    print("=== ULTRA COMPRESSION METRICS ===")
    print(f"Original: {res['metrics']['original_chars']} chars")
    print(f"Optimized: {res['metrics']['optimized_chars']} chars")
    print(f"Savings: {res['metrics']['compression_ratio']}")
    print(f"Full: {len(res['critical_files'])}, Stubs: {len(res['interface_stubs'])}")