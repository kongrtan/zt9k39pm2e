#!/usr/bin/env python3
"""Package each skill folder into dist/<name>.zip for Dify "Upload package".

Uses zipfile so entry paths always use "/" (Dify rejects "\\" in entry names,
which Windows PowerShell 5.1 Compress-Archive produces).

    python skills/build.py
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKIP = {"__pycache__", ".DS_Store", "Thumbs.db"}


def frontmatter_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        sys.exit(f"{skill_md}: missing frontmatter")
    name = re.search(r"^name:\s*(\S+)\s*$", match.group(1), re.M)
    if not name or not re.search(r"^description:\s*\S", match.group(1), re.M):
        sys.exit(f"{skill_md}: name and description are required")
    return name.group(1)


def build(skill_dir: Path) -> Path:
    name = frontmatter_name(skill_dir / "SKILL.md")
    if name != skill_dir.name or not NAME_RE.match(name) or len(name) > 64:
        sys.exit(f"{skill_dir}: name '{name}' must match the folder and [a-z0-9-], max 64")
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_dir() or SKIP.intersection(path.parts):
                continue
            # Top-level folder inside the zip; Dify strips it (single <name>/SKILL.md).
            zf.write(path, f"{name}/{path.relative_to(skill_dir).as_posix()}")
    return out


def main() -> None:
    for skill_md in sorted(ROOT.glob("*/SKILL.md")):
        out = build(skill_md.parent)
        print(f"{out.relative_to(ROOT.parent)}  {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
