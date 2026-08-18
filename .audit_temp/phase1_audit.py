#!/usr/bin/env python3
"""Phase 1 structural audit: circular imports, dead imports, duplicate symbols."""
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
PY_FILES = sorted(REPO.rglob("*.py"))

def is_under_venv(path):
    try:
        return ".venv" in path.parts
    except Exception:
        return False

PY_FILES = [p for p in PY_FILES if not is_under_venv(p)]

def parse(path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), str(path))
    except SyntaxError as e:
        print(f"SYNTAX_ERROR: {path}: {e}")
        return None

# 1. Circular imports via import graph
edges = defaultdict(list)  # importer -> imported
imports = defaultdict(list)
for path in PY_FILES:
    tree = parse(path)
    if tree is None:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "__future__":
                    continue
                if isinstance(node, ast.ImportFrom):
                    module = node.module or alias.name
                    # relative imports: resolve roughly
                    if node.level:
                        parts = path.relative_to(REPO).parent.parts
                        module = ".".join(parts[:len(parts)-node.level+1]) + (f".{module}" if module else "")
                    # ignore stdlib/third-party for circular analysis
                    if module and (module.startswith("commerceos") or module.startswith("scripts") or module.startswith("pages") or module.startswith("archive")):
                        edges[str(path.relative_to(REPO))].append(module)
                        imports[str(path.relative_to(REPO))].append((node.lineno, module, alias.name))

# Tarjan / DFS to find cycles
visited = set()
rec_stack = []
rec_set = set()
cycles = []

def dfs(node):
    visited.add(node)
    rec_stack.append(node)
    rec_set.add(node)
    for nxt in edges.get(node, []):
        if nxt not in visited:
            dfs(nxt)
        elif nxt in rec_set:
            idx = rec_stack.index(nxt)
            cycles.append(rec_stack[idx:] + [nxt])
    rec_stack.pop()
    rec_set.remove(node)

for n in list(edges.keys()):
    if n not in visited:
        dfs(n)

if cycles:
    print("== CIRCULAR IMPORT CYCLES ==")
    for c in cycles:
        print(" -> ".join(c))
else:
    print("== NO CIRCULAR IMPORT CYCLES DETECTED ==")

# 2. Dead imports: imported names never used in same file
print("\n== DEAD IMPORTS (imported name not referenced in same file) ==")
for path in PY_FILES:
    tree = parse(path)
    if tree is None:
        continue
    # collect names used in file
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # crude: base attribute chain root
            n = node.value
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                used_names.add(n.id)
    rel = str(path.relative_to(REPO))
    for lineno, module, name in imports.get(rel, []):
        asname = name
        # check if alias has asname
        # We can't easily recover asname from module/name alone; do best-effort regex
        # Only flag obvious cases where imported name not in used_names
        if name not in ("*",) and name not in used_names:
            print(f"{rel}:{lineno} possibly dead import `{name}` from `{module}`")

# 3. Duplicate class/function names across contexts
symbols = defaultdict(list)  # symbol -> [(context, file, lineno)]
for path in PY_FILES:
    tree = parse(path)
    if tree is None:
        continue
    rel = str(path.relative_to(REPO))
    ctx = path.relative_to(REPO / "commerceos").parts[0] if "commerceos" in path.parts else "root"
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name].append((ctx, rel, node.lineno))

print("\n== DUPLICATE SYMBOLS ACROSS CONTEXTS ==")
for name, locations in sorted(symbols.items()):
    contexts = {loc[0] for loc in locations}
    if len(contexts) > 1:
        # Filter to interesting names
        if any(k in name.lower() for k in ("telegram", "notifier", "syncengine", "mapper", "access_token", "engine", "service", "repository", "client")) or name in ("SyncEngine","Mapper","TelegramNotifier","get_access_token"):
            print(f"{name}: {len(locations)} occurrences across {len(contexts)} contexts")
            for ctx, rel, lineno in locations:
                print(f"  {rel}:{lineno} [{ctx}]")

# 4. Root scripts inventory
print("\n== ROOT PYTHON SCRIPTS ==")
for p in sorted(REPO.glob("*.py")):
    stat = p.stat()
    print(f"{p.name} size={stat.st_size} lines={sum(1 for _ in p.open())}")

print("\n== ARCHIVE IMPORTERS ==")
for rel in sorted(edges.keys()):
    if any("archive" in m for m in edges[rel]):
        print(f"{rel} imports {', '.join(m for m in edges[rel] if 'archive' in m)}")
