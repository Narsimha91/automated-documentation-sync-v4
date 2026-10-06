from pathlib import Path

import pytest

from src.features import features
from src.sync_readme import render_readme, sync_readme


def test_features_are_returned_in_declared_order() -> None:
    assert features() == [
        "Maintains an ordered Python source for README features",
        "Validates README markers before changing generated content",
        "Preserves README content outside generated feature bullets",
        "Skips writes when generated content is unchanged",
    ]


def test_render_preserves_markers_heading_and_non_bullet_content() -> None:
    original = (
        "before\n"
        "  <!-- docs-sync: start -->  \n"
        "# features\n"
        "- old feature\n"
        "  <!-- docs-sync: end -->\n"
        "after\n"
    )

    rendered = render_readme(original, ["second", "first"])

    assert rendered == (
        "before\n"
        "  <!-- docs-sync: start -->  \n"
        "# features\n"
        "- second\n"
        "- first\n"
        "  <!-- docs-sync: end -->\n"
        "after\n"
    )


def test_render_is_deterministic() -> None:
    original = "<!-- docs-sync: start -->\n# features\n<!-- docs-sync: end -->\n"
    feature_names = ["one", "two"]

    assert render_readme(original, feature_names) == render_readme(original, feature_names)


def test_multiline_feature_is_rejected_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme_path = tmp_path / "README.md"
    readme_text = "<!-- docs-sync: start -->\n# features\n<!-- docs-sync: end -->\n"
    readme_path.write_text(readme_text, encoding="utf-8")
    original_open = Path.open

    def forbid_write(self: Path, mode: str = "r", *args: object, **kwargs: object):
        if self == readme_path and "w" in mode:
            pytest.fail("multiline features must be rejected before writing")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", forbid_write)

    with pytest.raises(ValueError, match="single-line"):
        sync_readme(readme_path, ["feature\n<!-- docs-sync: end -->"])

    assert readme_path.read_text(encoding="utf-8") == readme_text


@pytest.mark.parametrize(
    "readme_text",
    [
        "# features\n<!-- docs-sync: end -->\n",
        "<!-- docs-sync: start -->\n# features\n",
        "<!-- docs-sync: start -->\n<!-- docs-sync: start -->\n"
        "# features\n<!-- docs-sync: end -->\n",
        "<!-- docs-sync: start -->\n# features\n<!-- docs-sync: end -->\n"
        "<!-- docs-sync: end -->\n",
        "<!-- docs-sync: end -->\n# features\n<!-- docs-sync: start -->\n",
        "<!-- docs-sync: start -->\nnot the heading\n<!-- docs-sync: end -->\n",
    ],
)
def test_malformed_readme_is_rejected_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, readme_text: str
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme_text, encoding="utf-8")
    original_open = Path.open

    def forbid_write(self: Path, mode: str = "r", *args: object, **kwargs: object):
        if self == readme_path and "w" in mode:
            pytest.fail("malformed README must not be opened for writing")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", forbid_write)

    with pytest.raises(ValueError):
        sync_readme(readme_path, ["new feature"])

    assert readme_path.read_text(encoding="utf-8") == readme_text


def test_sync_does_not_open_readme_for_writing_when_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme_path = tmp_path / "README.md"
    readme_text = "<!-- docs-sync: start -->\n# features\n- one\n<!-- docs-sync: end -->\n"
    readme_path.write_text(readme_text, encoding="utf-8")
    original_open = Path.open

    def forbid_write(self: Path, mode: str = "r", *args: object, **kwargs: object):
        if self == readme_path and "w" in mode:
            pytest.fail("unchanged README must not be opened for writing")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", forbid_write)

    assert sync_readme(readme_path, ["one"]) is False


def test_sync_writes_changed_output_once(tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "<!-- docs-sync: start -->\n# features\n- old\n<!-- docs-sync: end -->\n",
        encoding="utf-8",
    )

    assert sync_readme(readme_path, ["new"]) is True
    assert readme_path.read_text(encoding="utf-8") == (
        "<!-- docs-sync: start -->\n# features\n- new\n<!-- docs-sync: end -->\n"
    )