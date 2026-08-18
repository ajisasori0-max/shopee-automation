#!/usr/bin/env python3
"""Phase 1 structural audit v2."""
import ast
import importlib
import importlib.util
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
sys.path.insert(0, str(REPO))

# 1. Bounded contexts vs ARCHITECTURE.md
print("=" * 60)
print("1. BOUNDED CONTEXTS vs ARCHITECTURE.md")
print("=" * 60)
arch_expected = {
    "platform", "ingestion", "commerce", "monitoring", "intelligence",
    "decision", "execution", "events", "dashboard", "connectors"
}
actual_ctx = set()
shell_contexts = []
for p in (REPO / "commerceos").iterdir():
    if p.is_dir() and (p / "__init__.py").exists():
        actual_ctx.add(p.name)
        py_files = list(p.rglob("*.py"))
        non_init = [f for f in py_files if f.name != "__init__.py"]
        if not non_init:
            shell_contexts.append(p.name)

print(f"Expected per ARCHITECTURE.md ({len(arch_expected)}): {sorted(arch_expected)}")
print(f"Actual contexts in commerceos/ ({len(actual_ctx)}): {sorted(actual_ctx)}")
print(f"Only in ARCHITECTURE.md: {sorted(arch_expected - actual_ctx)}")
print(f"Extra contexts in repo: {sorted(actual_ctx - arch_expected)}")
print(f"__init__.py-only shell contexts ({len(shell_contexts)}):")
for c in sorted(shell_contexts):
    print(f"  - commerceos/{c}/")

# 2. Circular imports via runtime import attempts
print("\n" + "=" * 60)
print("2. CIRCULAR / RUNTIME IMPORT ERRORS")
print("=" * 60)
# Find all commerceos modules
modules = []
for f in sorted((REPO / "commerceos").rglob("*.py")):
    rel = f.relative_to(REPO)
    mod = str(rel.with_suffix("")).replace(os.sep, ".")
    modules.append((mod, f))

failed_imports = []
for mod, f in modules:
    if "__pycache__" in mod:
        continue
    try:
        spec = importlib.util.spec_from_file_location(mod, f)
        if spec and spec.loader:
            mod_obj = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod_obj)
    except Exception as e:
        failed_imports.append((mod, f, type(e).__name__, str(e)[:200]))

if failed_imports:
    for mod, f, etype, emsg in failed_imports:
        print(f"{f}:{etype}: {emsg}")
else:
    print("No runtime import errors detected on individual module load.")

# 3. Active archive imports
print("\n" + "=" * 60)
print("3. ACTIVE IMPORTS FROM archive/")
print("=" * 60)
archive_importers = []
for f in sorted(REPO.rglob("*.py")):
    if ".venv" in f.parts or "__pycache__" in f.parts:
        continue
    text = f.read_text(errors="ignore")
    if "from archive" in text or "import archive" in text:
        for i, line in enumerate(text.splitlines(), 1):
            if "from archive" in line or "import archive" in line:
                archive_importers.append((f.relative_to(REPO), i, line.strip()))
for rel, ln, line in archive_importers:
    print(f"{rel}:{ln}: {line}")
if not archive_importers:
    print("No active archive imports found.")

# 4. Duplicate symbols across contexts
print("\n" + "=" * 60)
print("4. DUPLICATE CLASSES/FUNCTIONS ACROSS CONTEXTS")
print("=" * 60)
symbols = defaultdict(list)
interesting = {"TelegramNotifier", "Mapper", "SyncEngine", "get_access_token",
               "ShopeeApiClient", "DashboardQueryService", "Engine", "Service",
               "Repository", "Client", "Notifier", "Executor", "Rules"}
for f in sorted((REPO / "commerceos").rglob("*.py")):
    if "__pycache__" in f.parts:
        continue
    text = f.read_text(errors="ignore")
    try:
        tree = ast.parse(text, str(f))
    except SyntaxError:
        continue
    ctx = f.relative_to(REPO / "commerceos").parts[0] if f.parts else "root"
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name].append((ctx, f.relative_to(REPO), node.lineno))

for name, locs in sorted(symbols.items()):
    contexts = {loc[0] for loc in locs}
    if len(contexts) > 1 and (name in interesting or any(k in name for k in interesting)):
        print(f"\n{name} ({len(locs)} occurrences across {len(contexts)} contexts):")
        for ctx, rel, ln in locs:
            print(f"  {rel}:{ln} [{ctx}]")

# 5. Root scripts inventory and flagging
print("\n" + "=" * 60)
print("5. ROOT SCRIPTS (debug / test / auth scratch)")
print("=" * 60)
flags = {"debug": [], "test": [], "auth": [], "demo": [], "other": []}
for f in sorted(REPO.glob("*.py")):
    name = f.name.lower()
    lines = sum(1 for _ in f.open(errors="ignore"))
    entry = f"{f.name} ({f.stat().st_size} bytes, {lines} lines)"
    if "debug" in name:
        flags["debug"].append(entry)
    elif name.startswith("test_") or name.startswith("check_") or "test" in name:
        flags["test"].append(entry)
    elif "auth" in name:
        flags["auth"].append(entry)
    elif "demo" in name:
        flags["demo"].append(entry)
    else:
        flags["other"].append(entry)

for cat in ["debug", "test", "auth", "demo", "other"]:
    print(f"\n{cat.upper()} ({len(flags[cat])}):")
    for e in flags[cat]:
        print(f"  - {e}")
