"""Synchronize code blocks in README.md with source files in examples/."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
README_PATH = ROOT_DIR / "README.md"

LANG_MAP = {
    ".csv": "csv",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".tex": "latex",
    ".py": "python",
    ".txt": "latex",
}

BLOCK_REGEX = re.compile(
    r"(<!--\s*START:(?P<filepath>[^\s>]+)\s*-->).*?(<!--\s*END:(?P=filepath)\s*-->)",
    re.DOTALL,
)


def update_readme(check_only: bool = False) -> bool:
    content = README_PATH.read_text(encoding="utf-8")

    def replacer(match: re.Match) -> str:
        rel_path = match.group("filepath")
        start_tag = f"<!-- START:{rel_path} -->"
        end_tag = f"<!-- END:{rel_path} -->"

        file_path = ROOT_DIR / rel_path
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found for auto-insertion: {file_path}")

        file_content = file_path.read_text(encoding="utf-8").strip()
        ext = file_path.suffix.lower()
        lang = LANG_MAP.get(ext, "")

        return f"{start_tag}\n```{lang}\n{file_content}\n```\n{end_tag}"

    new_content = BLOCK_REGEX.sub(replacer, content)

    if new_content != content:
        if check_only:
            return False
        README_PATH.write_text(new_content, encoding="utf-8")
        print(f"Updated {README_PATH}")
        return True
    return True


if __name__ == "__main__":
    check_mode = "--check" in sys.argv
    success = update_readme(check_only=check_mode)
    if not success:
        print(
            "README.md examples are out of date with examples/. "
            "Run 'python scripts/update_readme_examples.py' to synchronize."
        )
        sys.exit(1)
