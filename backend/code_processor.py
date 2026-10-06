import os
from pathlib import Path

IGNORED_DIRS = {
    ".git", "venv", ".venv", "env", "node_modules", "__pycache__", "dist",
    "build", "coverage", ".next", ".idea", ".pytest_cache", ".mypy_cache",
    "target", "vendor", "site-packages", "repolens_"
}
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".c", ".h",
    ".cs", ".go", ".rs", ".php", ".html", ".css", ".sql"
}
PRIORITY_NAMES = {
    "readme.md": 0, "readme": 1, "main.py": 2, "app.py": 3, "server.py": 4,
    "index.py": 5, "requirements.txt": 6, "package.json": 7, "pom.xml": 8,
    "build.gradle": 9, "pyproject.toml": 10, "dockerfile": 11
}
MAX_FILES = 18
MAX_FILE_CHARS = 5000
MAX_TOTAL_CHARS = 24000
MAX_TREE_FILES = 160


def _is_ignored_file(path: Path) -> bool:
    name = path.name.lower()
    if name in {".env", ".ds_store", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return True
    if name.endswith((".min.js", ".map", ".lock", ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip")):
        return True
    if name.startswith("test_") or name.endswith(("_test.py", ".spec.js", ".test.js", ".spec.ts", ".test.ts")):
        return True
    return False


def _priority(path: Path) -> tuple:
    name = path.name.lower()
    if name in PRIORITY_NAMES:
        return (0, PRIORITY_NAMES[name], len(path.parts), str(path).lower())
    if path.suffix.lower() in SOURCE_EXTENSIONS:
        return (1, 0, len(path.parts), str(path).lower())
    if name.endswith(".md"):
        return (2, 0, len(path.parts), str(path).lower())
    return (3, 0, len(path.parts), str(path).lower())


def build_repository_context(repo_path: str) -> dict:
    """Collect a bounded, prioritized snapshot of a repository for the LLM."""
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("The cloned repository folder could not be found.")

    all_files = []
    tree_lines = []
    for current, dirs, filenames in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith("."))
        current_path = Path(current)
        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root)
            if _is_ignored_file(path):
                continue
            try:
                if path.stat().st_size > 500_000:
                    continue
            except OSError:
                continue
            all_files.append(path)
            if len(tree_lines) < MAX_TREE_FILES:
                tree_lines.append(str(relative).replace("\\", "/"))

    if not all_files:
        raise ValueError("No readable source or documentation files were found in this repository.")

    selected = sorted(all_files, key=lambda p: _priority(p))[:MAX_FILES]
    chunks = []
    used_chars = 0
    included_files = []
    for path in selected:
        if used_chars >= MAX_TOTAL_CHARS:
            break
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        content = content.strip()
        if not content:
            continue
        budget = min(MAX_FILE_CHARS, MAX_TOTAL_CHARS - used_chars)
        if len(content) > budget:
            content = content[:budget] + "\n... [file truncated to fit context limit]"
        relative = str(path.relative_to(root)).replace("\\", "/")
        chunks.append(f"===== FILE: {relative} =====\n{content}")
        included_files.append(relative)
        used_chars += len(content)

    if not chunks:
        raise ValueError("The repository did not contain any readable text files.")

    return {
        "repository_name": root.name,
        "file_count": len(all_files),
        "analyzed_file_count": len(included_files),
        "important_files": included_files,
        "structure": tree_lines,
        "context_text": "\n\n".join(chunks),
    }
