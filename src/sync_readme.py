"""Synchronize the README feature bullets from the ordered feature source."""

import argparse
from pathlib import Path
import sys
from collections.abc import Sequence

from src.features import features


START_MARKER = "<!-- docs-sync: start -->"
END_MARKER = "<!-- docs-sync: end -->"
FEATURES_HEADING = "# features"
DEFAULT_README = Path(__file__).resolve().parent.parent / "README.md"


def _line_content(line: str) -> str:
    return line.removesuffix("\n").removesuffix("\r")


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return "\n"


def _marker_indices(lines: list[str]) -> tuple[int, int]:
    start_indices = [index for index, line in enumerate(lines) if line.strip() == START_MARKER]
    end_indices = [index for index, line in enumerate(lines) if line.strip() == END_MARKER]
    if len(start_indices) != 1 or len(end_indices) != 1:
        raise ValueError("README must contain exactly one start marker and one end marker")

    start_index, end_index = start_indices[0], end_indices[0]
    if start_index >= end_index:
        raise ValueError("README start marker must appear before its end marker")
    return start_index, end_index


def render_readme(readme_text: str, feature_names: Sequence[str]) -> str:
    lines = readme_text.splitlines(keepends=True)
    start_index, end_index = _marker_indices(lines)
    section_lines = lines[start_index + 1 : end_index]

    if not section_lines or _line_content(section_lines[0]) != FEATURES_HEADING:
        raise ValueError("README markers must enclose the '# features' heading")
    if not section_lines[0].endswith(("\n", "\r")):
        raise ValueError("README features heading must be on its own line")
    if any(not _line_content(line).startswith("- ") for line in section_lines[1:]):
        raise ValueError("README features section may contain only the heading and bullets")
    if any(not isinstance(feature, str) or "\n" in feature or "\r" in feature for feature in feature_names):
        raise ValueError("feature names must be single-line strings")

    newline = _line_ending(section_lines[0])
    bullet_lines = [f"- {feature}{newline}" for feature in feature_names]
    return "".join(
        lines[: start_index + 1]
        + [section_lines[0]]
        + bullet_lines
        + lines[end_index:]
    )


def sync_readme(
    readme_path: str | Path = DEFAULT_README,
    feature_names: Sequence[str] | None = None,
) -> bool:
    path = Path(readme_path)
    with path.open("r", encoding="utf-8", newline="") as readme_file:
        original = readme_file.read()

    # Validate the README before retrieving features or opening it for writing.
    lines = original.splitlines(keepends=True)
    _marker_indices(lines)
    if feature_names is None:
        feature_names = features()
    updated = render_readme(original, feature_names)
    if updated == original:
        return False

    with path.open("w", encoding="utf-8", newline="") as readme_file:
        readme_file.write(updated)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=Path,
        default=DEFAULT_README,
        help="README path (defaults to the repository README)",
    )
    arguments = parser.parse_args(argv)
    try:
        changed = sync_readme(arguments.readme)
    except ValueError as error:
        print(f"README synchronization failed: {error}", file=sys.stderr)
        return 1

    print("README updated" if changed else "README already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())