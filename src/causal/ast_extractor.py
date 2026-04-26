"""
AST Extractor

Extracts semantic dependencies (imports, function calls, class usage)
from Python source code to build the causal graph.
"""

import ast
from pathlib import Path
from typing import List, Dict, Set

class DependencyExtractor(ast.NodeVisitor):
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.imports: Set[str] = set()
        self.calls: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)

def extract_dependencies(file_path: Path) -> Dict[str, List[str]]:
    """Parse a python file and extract its dependencies."""
    if not file_path.exists() or file_path.suffix != '.py':
        return {"imports": [], "calls": []}

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        # Simple module name extraction based on file path for this prototype
        module_name = file_path.stem 
        extractor = DependencyExtractor(module_name)
        extractor.visit(tree)
        
        return {
            "imports": list(extractor.imports),
            "calls": list(extractor.calls)
        }
    except Exception as e:
        # Ignore syntax errors or parsing issues for now
        return {"imports": [], "calls": []}

