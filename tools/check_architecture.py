"""Check module boundaries, dependency order, syntax and the 500-line limit."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
modules = ast.parse((ROOT / "backend/app/modules/__init__.py").read_text(encoding="utf-8"))
order = next(ast.literal_eval(node.value) for node in modules.body
             if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "MODULES" for t in node.targets))
errors = []
files = []
for directory in ("backend/app", "backend/tests", "backend/migrations", "frontend", "tools"):
    files.extend(p for p in (ROOT / directory).rglob("*")
                 if p.suffix in (".py", ".js", ".css", ".html") and "__pycache__" not in p.parts)
for path in files:
    source = path.read_text(encoding="utf-8-sig")
    relative = path.relative_to(ROOT)
    if len(source.splitlines()) >= 500:
        errors.append(f"{relative}: {len(source.splitlines())} lines (must be under 500)")
    if path.suffix != ".py":
        continue
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        errors.append(f"{relative}: {error}")
        continue
    if "modules" not in path.parts or path.parent.name not in order:
        continue
    owner = path.parent.name
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        for name in names:
            parts = name.split(".")
            if len(parts) < 4 or parts[:2] != ["app", "modules"] or parts[2] == owner:
                continue
            target, component = parts[2:4]
            if component == "models":
                errors.append(f"{relative}:{node.lineno}: imports {target}'s models")
            if path.stem.startswith("service") and component.startswith("service") and order.index(target) >= order.index(owner):
                errors.append(f"{relative}:{node.lineno}: service depends on later module {target}")
print(f"Checked {len(files)} source files and {len(order)} module boundaries.")
for error in sorted(set(errors)):
    print(error)
raise SystemExit(bool(errors))
