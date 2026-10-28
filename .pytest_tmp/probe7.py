import ast
import pathlib

source = pathlib.Path("features/world_watch/skill.py").read_text(encoding="utf-8")
tree = ast.parse(source)
print("file lines:", source.count("\n"))
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        print("def", node.name, "at line", node.lineno)
print("---")
print("execute count:", sum(1 for node in tree.body
                            if isinstance(node, ast.FunctionDef) and node.name == "execute"))
