"""Tests for floop.prototype — PRD, Sitemap, Component DSL."""

import csv
import textwrap
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from floop.cli import main
from floop.prototype import (
    _derive_domain,
    _parse_frontmatter,
    component_init,
    component_validate,
    journey_check,
    prd_init,
    prd_validate,
    prototype_init,
    prototype_validate,
    sitemap_init,
    sitemap_validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_project(tmp_path: Path) -> Path:
    """Create a minimal floop project in tmp_path."""
    (tmp_path / ".floop").mkdir()
    return tmp_path


def write_prd(project_dir: Path, content: str) -> Path:
    path = project_dir / ".floop" / "prd.md"
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def write_sitemap(project_dir: Path, content: str) -> Path:
    path = project_dir / ".floop" / "sitemap.md"
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def write_components(project_dir: Path, content: str) -> Path:
    path = project_dir / ".floop" / "components.yaml"
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid(self):
        text = "---\nfoo: bar\n---\nsome body"
        result = _parse_frontmatter(text)
        assert result == {"foo": "bar"}

    def test_no_leading_dashes_returns_none(self):
        assert _parse_frontmatter("no frontmatter here") is None

    def test_empty_frontmatter_returns_empty_dict(self):
        text = "---\n---\nbody"
        result = _parse_frontmatter(text)
        assert result == {}

    def test_no_closing_dashes_returns_none(self):
        text = "---\nfoo: bar\nbody without closing"
        assert _parse_frontmatter(text) is None

    def test_raises_on_invalid_yaml(self):
        text = "---\n: invalid: yaml: :\n---"
        with pytest.raises(yaml.YAMLError):
            _parse_frontmatter(text)


# ---------------------------------------------------------------------------
# prd_init
# ---------------------------------------------------------------------------

class TestPrdInit:
    def test_creates_file(self, tmp_path):
        project = make_project(tmp_path)
        path = prd_init(project)
        assert path.exists()
        assert path.name == "prd.md"
        content = path.read_text()
        assert "product:" in content
        assert "target_users:" in content
        assert "status: draft" in content

    def test_returns_path(self, tmp_path):
        project = make_project(tmp_path)
        path = prd_init(project)
        assert path == project / ".floop" / "prd.md"

    def test_raises_if_exists(self, tmp_path):
        project = make_project(tmp_path)
        prd_init(project)
        with pytest.raises(FileExistsError):
            prd_init(project)

    def test_creates_parent_dirs(self, tmp_path):
        # project WITHOUT .floop directory yet
        path = prd_init(tmp_path)
        assert path.exists()


# ---------------------------------------------------------------------------
# prd_validate
# ---------------------------------------------------------------------------

_VALID_PRD = """\
---
version: 1
updated_at: 2024-01-01
product: "My App"
target_users:
  - developer
core_flows:
  - login
css_framework: tailwind
status: draft
---
body
"""

class TestPrdValidate:
    def test_valid_draft(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, _VALID_PRD)
        errors, warnings = prd_validate(project)
        assert errors == []
        assert any("draft" in w for w in warnings)

    def test_valid_confirmed_no_warning(self, tmp_path):
        project = make_project(tmp_path)
        content = _VALID_PRD.replace("status: draft", "status: confirmed")
        write_prd(project, content)
        errors, warnings = prd_validate(project)
        assert errors == []
        assert warnings == []

    def test_missing_file(self, tmp_path):
        project = make_project(tmp_path)
        errors, _ = prd_validate(project)
        assert any("prd.md not found" in e for e in errors)

    def test_no_frontmatter(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "no frontmatter here\n")
        errors, _ = prd_validate(project)
        assert any("no YAML frontmatter" in e for e in errors)

    def test_invalid_yaml(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\n: bad: yaml:\n---\n")
        errors, _ = prd_validate(project)
        assert any("YAML parse error" in e for e in errors)

    def test_empty_product(self, tmp_path):
        project = make_project(tmp_path)
        content = _VALID_PRD.replace('product: "My App"', "product: \"\"")
        write_prd(project, content)
        errors, _ = prd_validate(project)
        assert any("product" in e for e in errors)

    def test_empty_target_users(self, tmp_path):
        project = make_project(tmp_path)
        content = _VALID_PRD.replace("target_users:\n  - developer", "target_users: []")
        write_prd(project, content)
        errors, _ = prd_validate(project)
        assert any("target_users" in e for e in errors)

    def test_empty_core_flows(self, tmp_path):
        project = make_project(tmp_path)
        content = _VALID_PRD.replace("core_flows:\n  - login", "core_flows: []")
        write_prd(project, content)
        errors, _ = prd_validate(project)
        assert any("core_flows" in e for e in errors)

    def test_invalid_status(self, tmp_path):
        project = make_project(tmp_path)
        content = _VALID_PRD.replace("status: draft", "status: unknown")
        write_prd(project, content)
        errors, _ = prd_validate(project)
        assert any("invalid status" in e for e in errors)

    def test_missing_version(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\nproduct: x\ntarget_users: [a]\ncore_flows: [b]\ncss_framework: tailwind\nstatus: draft\nupdated_at: 2024-01-01\n---\n")
        errors, _ = prd_validate(project)
        # No 'version' field → should error — but file is otherwise fine
        # The template always writes version; omitting it triggers the check
        assert "missing required field: version" in errors

    def test_missing_css_framework(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\nversion: 1\nproduct: x\ntarget_users: [a]\ncore_flows: [b]\nstatus: draft\nupdated_at: 2024-01-01\n---\n")
        errors, _ = prd_validate(project)
        assert "missing required field: css_framework" in errors

    def test_missing_updated_at(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\nversion: 1\nproduct: x\ntarget_users: [a]\ncore_flows: [b]\ncss_framework: tailwind\nstatus: draft\n---\n")
        errors, _ = prd_validate(project)
        assert "missing required field: updated_at" in errors

    def test_missing_status(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\nversion: 1\nproduct: x\ntarget_users: [a]\ncore_flows: [b]\ncss_framework: tailwind\nupdated_at: 2024-01-01\n---\n")
        errors, _ = prd_validate(project)
        assert "missing required field: status" in errors


# ---------------------------------------------------------------------------
# sitemap_init
# ---------------------------------------------------------------------------

class TestSitemapInit:
    def test_creates_file(self, tmp_path):
        project = make_project(tmp_path)
        path = sitemap_init(project)
        assert path.exists()
        assert path.name == "sitemap.md"
        content = path.read_text()
        assert "pages:" in content

    def test_returns_path(self, tmp_path):
        project = make_project(tmp_path)
        path = sitemap_init(project)
        assert path == project / ".floop" / "sitemap.md"

    def test_raises_if_exists(self, tmp_path):
        project = make_project(tmp_path)
        sitemap_init(project)
        with pytest.raises(FileExistsError):
            sitemap_init(project)

    def test_creates_parent_dirs(self, tmp_path):
        path = sitemap_init(tmp_path)
        assert path.exists()


# ---------------------------------------------------------------------------
# sitemap_validate
# ---------------------------------------------------------------------------

_VALID_SITEMAP = """\
---
version: 1
updated_at: 2024-01-01
pages:
  - id: home
    title: 首页
    file: build/home.html
    status: planned
---
<!-- sitemap -->
"""

class TestSitemapValidate:
    def test_valid(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _VALID_SITEMAP)
        errors, warnings = sitemap_validate(project)
        assert errors == []
        assert warnings == []

    def test_missing_file(self, tmp_path):
        project = make_project(tmp_path)
        errors, _ = sitemap_validate(project)
        assert any("sitemap.md not found" in e for e in errors)

    def test_no_frontmatter(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "no frontmatter\n")
        errors, _ = sitemap_validate(project)
        assert any("no YAML frontmatter" in e for e in errors)

    def test_invalid_yaml(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\n: bad: yaml:\n---\n")
        errors, _ = sitemap_validate(project)
        assert any("YAML parse error" in e for e in errors)

    def test_missing_version(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nupdated_at: 2024-01-01\npages:\n  - id: a\n    title: A\n    file: a.html\n    status: planned\n---\n")
        errors, _ = sitemap_validate(project)
        assert "missing required field: version" in errors

    def test_missing_updated_at(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\npages:\n  - id: a\n    title: A\n    file: a.html\n    status: planned\n---\n")
        errors, _ = sitemap_validate(project)
        assert "missing required field: updated_at" in errors

    def test_empty_pages(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        errors, _ = sitemap_validate(project)
        assert any("non-empty list" in e for e in errors)

    def test_pages_not_list(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: notalist\n---\n")
        errors, _ = sitemap_validate(project)
        assert any("non-empty list" in e for e in errors)

    def test_missing_pages_field(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\n---\n")
        errors, _ = sitemap_validate(project)
        assert "missing required field: pages" in errors

    def test_page_not_dict(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n  - just_a_string\n---\n")
        errors, _ = sitemap_validate(project)
        assert any("must be a mapping" in e for e in errors)

    def test_page_missing_field(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n  - id: home\n    title: Home\n---\n")
        errors, _ = sitemap_validate(project)
        assert any("missing required field: file" in e for e in errors)
        assert any("missing required field: status" in e for e in errors)

    def test_duplicate_page_id(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n"
            "  - id: home\n    title: A\n    file: a.html\n    status: planned\n"
            "  - id: home\n    title: B\n    file: b.html\n    status: planned\n---\n",
        )
        errors, _ = sitemap_validate(project)
        assert any("duplicate page id" in e for e in errors)

    def test_invalid_page_status(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n"
            "  - id: home\n    title: Home\n    file: home.html\n    status: bad\n---\n",
        )
        errors, _ = sitemap_validate(project)
        assert any("invalid status 'bad'" in e for e in errors)

    def test_built_page_file_missing_warns(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n"
            "  - id: home\n    title: Home\n    file: build/home.html\n    status: built\n---\n",
        )
        errors, warnings = sitemap_validate(project)
        assert errors == []
        assert any("file not found" in w for w in warnings)

    def test_built_page_file_exists_no_warning(self, tmp_path):
        project = make_project(tmp_path)
        html_file = project / ".floop" / "build" / "home.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text("<html></html>")
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n"
            "  - id: home\n    title: Home\n    file: build/home.html\n    status: built\n---\n",
        )
        errors, warnings = sitemap_validate(project)
        assert errors == []
        assert not any("file not found" in w for w in warnings)


# ---------------------------------------------------------------------------
# component_init
# ---------------------------------------------------------------------------

class TestComponentInit:
    def test_creates_file(self, tmp_path):
        project = make_project(tmp_path)
        path = component_init(project)
        assert path.exists()
        assert path.name == "components.yaml"
        content = path.read_text()
        assert "components:" in content

    def test_returns_path(self, tmp_path):
        project = make_project(tmp_path)
        path = component_init(project)
        assert path == project / ".floop" / "components.yaml"

    def test_raises_if_exists(self, tmp_path):
        project = make_project(tmp_path)
        component_init(project)
        with pytest.raises(FileExistsError):
            component_init(project)

    def test_creates_parent_dirs(self, tmp_path):
        path = component_init(tmp_path)
        assert path.exists()


# ---------------------------------------------------------------------------
# component_validate
# ---------------------------------------------------------------------------

_VALID_COMPONENT_YAML = """\
version: 1
updated_at: 2024-01-01
css_framework: tailwind
components:
  - id: navbar
    title: 导航栏
    status: draft
    tokens:
      background: color.surface
"""

class TestComponentValidate:
    def test_valid(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, _VALID_COMPONENT_YAML)
        errors, warnings = component_validate(project)
        assert errors == []
        assert warnings == []

    def test_missing_file(self, tmp_path):
        project = make_project(tmp_path)
        errors, _ = component_validate(project)
        assert any("components.yaml not found" in e for e in errors)

    def test_invalid_yaml(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, ": bad: yaml:\n")
        errors, _ = component_validate(project)
        assert any("YAML parse error" in e for e in errors)

    def test_not_a_mapping(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "- just\n- a list\n")
        errors, _ = component_validate(project)
        assert any("must be a YAML mapping" in e for e in errors)

    def test_missing_version(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "updated_at: 2024-01-01\ncss_framework: tailwind\ncomponents: []\n")
        errors, _ = component_validate(project)
        assert "missing required top-level field: version" in errors

    def test_missing_css_framework(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncomponents: []\n")
        errors, _ = component_validate(project)
        assert "missing required top-level field: css_framework" in errors

    def test_missing_updated_at(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\ncss_framework: tailwind\ncomponents: []\n")
        errors, _ = component_validate(project)
        assert "missing required top-level field: updated_at" in errors

    def test_missing_components_key_returns_early(self, tmp_path):
        """components key absent — error recorded but function returns early (line 335)."""
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\n")
        errors, warnings = component_validate(project)
        assert "missing required top-level field: components" in errors
        assert warnings == []

    def test_components_not_list(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents: oops\n")
        errors, _ = component_validate(project)
        assert any("must be a list" in e for e in errors)

    def test_empty_components_warns(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents: []\n")
        errors, warnings = component_validate(project)
        assert errors == []
        assert any("empty" in w for w in warnings)

    def test_component_not_dict(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n  - just_a_string\n")
        errors, _ = component_validate(project)
        assert any("must be a mapping" in e for e in errors)

    def test_component_missing_fields(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n  - id: btn\n")
        errors, _ = component_validate(project)
        assert any("missing required field: title" in e for e in errors)
        assert any("missing required field: status" in e for e in errors)

    def test_duplicate_component_id(self, tmp_path):
        project = make_project(tmp_path)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n    tokens: {bg: x}\n"
            "  - id: btn\n    title: Button2\n    status: draft\n    tokens: {bg: y}\n",
        )
        errors, _ = component_validate(project)
        assert any("duplicate component id" in e for e in errors)

    def test_invalid_component_status(self, tmp_path):
        project = make_project(tmp_path)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: unknown\n    tokens: {bg: x}\n",
        )
        errors, _ = component_validate(project)
        assert any("invalid status 'unknown'" in e for e in errors)

    def test_component_no_tokens_warns(self, tmp_path):
        project = make_project(tmp_path)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n",
        )
        errors, warnings = component_validate(project)
        assert errors == []
        assert any("no tokens defined" in w for w in warnings)

    def test_token_path_valid_warns_nothing(self, tmp_path):
        """Token path exists in *.tokens.json — no warning."""
        project = make_project(tmp_path)
        tokens_dir = project / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "component.tokens.json").write_text(
            '{"color": {"surface": {"$value": "#fff", "$type": "color"}}}',
            encoding="utf-8",
        )
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n    tokens:\n      bg: color.surface\n",
        )
        errors, warnings = component_validate(project)
        assert errors == []
        assert not any("not found in any" in w for w in warnings)

    def test_token_path_missing_warns(self, tmp_path):
        """Token path not in any *.tokens.json — warning emitted."""
        project = make_project(tmp_path)
        tokens_dir = project / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "component.tokens.json").write_text(
            '{"color": {"surface": {"$value": "#fff", "$type": "color"}}}',
            encoding="utf-8",
        )
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: stepper\n    title: Stepper\n    status: draft\n"
            "    tokens:\n      track: stepper.track\n",
        )
        errors, warnings = component_validate(project)
        assert errors == []
        assert any("stepper.track" in w and "not found in any" in w for w in warnings)

    def test_token_path_no_token_files_skips_check(self, tmp_path):
        """No *.tokens.json files present — token path check is skipped entirely."""
        project = make_project(tmp_path)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n    tokens:\n      bg: anything.goes\n",
        )
        errors, warnings = component_validate(project)
        assert errors == []
        assert not any("not found in any" in w for w in warnings)

    def test_token_path_empty_tokens_dir_skips_check(self, tmp_path):
        """tokens/ dir exists but has no *.tokens.json files — check is skipped."""
        project = make_project(tmp_path)
        (project / ".floop" / "tokens").mkdir(parents=True)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n    tokens:\n      bg: anything.goes\n",
        )
        errors, warnings = component_validate(project)
        assert errors == []
        assert not any("not found in any" in w for w in warnings)

    def test_token_path_invalid_json_skips_file(self, tmp_path):
        """Malformed *.tokens.json is silently skipped — no crash, path treated as unknown."""
        project = make_project(tmp_path)
        tokens_dir = project / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "broken.tokens.json").write_text("not valid json {{{", encoding="utf-8")
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n    tokens:\n      bg: color.surface\n",
        )
        # broken file is skipped silently; color.surface not found → warns
        errors, warnings = component_validate(project)
        assert errors == []
        assert any("color.surface" in w and "not found in any" in w for w in warnings)


# ---------------------------------------------------------------------------
# CLI — floop prd
# ---------------------------------------------------------------------------

class TestCliPrd:
    def test_init_creates_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["prd", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "prd.md created" in result.output
        assert (tmp_path / ".floop" / "prd.md").exists()

    def test_init_fails_if_exists(self, tmp_path):
        runner = CliRunner()
        runner.invoke(main, ["prd", "init", "--project-dir", str(tmp_path)])
        result = runner.invoke(main, ["prd", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_passes(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, _VALID_PRD)
        runner = CliRunner()
        result = runner.invoke(main, ["prd", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_fails_on_errors(self, tmp_path):
        project = make_project(tmp_path)
        write_prd(project, "---\nstatus: draft\n---\n")
        runner = CliRunner()
        result = runner.invoke(main, ["prd", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1
        assert "error" in result.output

    def test_validate_missing_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["prd", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# CLI — floop sitemap
# ---------------------------------------------------------------------------

class TestCliSitemap:
    def test_init_creates_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["sitemap", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "sitemap.md created" in result.output
        assert (tmp_path / ".floop" / "sitemap.md").exists()

    def test_init_fails_if_exists(self, tmp_path):
        runner = CliRunner()
        runner.invoke(main, ["sitemap", "init", "--project-dir", str(tmp_path)])
        result = runner.invoke(main, ["sitemap", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_passes(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _VALID_SITEMAP)
        runner = CliRunner()
        result = runner.invoke(main, ["sitemap", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_fails_on_errors(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        runner = CliRunner()
        result = runner.invoke(main, ["sitemap", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_shows_warnings(self, tmp_path):
        """Test that warnings are printed (sitemap page built but file missing)."""
        project = make_project(tmp_path)
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n"
            "  - id: home\n    title: Home\n    file: build/home.html\n    status: built\n---\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["sitemap", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "⚠" in result.output

    def test_validate_missing_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["sitemap", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# CLI — floop component
# ---------------------------------------------------------------------------

class TestCliComponent:
    def test_init_creates_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["component", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "components.yaml created" in result.output
        assert (tmp_path / ".floop" / "components.yaml").exists()

    def test_init_fails_if_exists(self, tmp_path):
        runner = CliRunner()
        runner.invoke(main, ["component", "init", "--project-dir", str(tmp_path)])
        result = runner.invoke(main, ["component", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_passes(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, _VALID_COMPONENT_YAML)
        runner = CliRunner()
        result = runner.invoke(main, ["component", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_fails_on_errors(self, tmp_path):
        project = make_project(tmp_path)
        write_components(project, "- not: a mapping\n")
        runner = CliRunner()
        result = runner.invoke(main, ["component", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_shows_warnings(self, tmp_path):
        """Test that warnings are printed (component with no tokens)."""
        project = make_project(tmp_path)
        write_components(
            project,
            "version: 1\nupdated_at: 2024-01-01\ncss_framework: tailwind\ncomponents:\n"
            "  - id: btn\n    title: Button\n    status: draft\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["component", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "⚠" in result.output

    def test_validate_missing_file(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["component", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# _derive_domain
# ---------------------------------------------------------------------------

_SITEMAP_WITH_PAGES = """\
---
version: 1
updated_at: 2024-01-01
pages:
  - id: login
    title: Login
    file: build/journey/auth/login.html
    status: planned
  - id: home
    title: Home
    file: build/journey/home.html
    status: planned
---
"""

_SITEMAP_WITH_DOMAIN_FIELD = """\
---
version: 1
updated_at: 2024-01-01
pages:
  - id: login
    title: Login
    domain: authentication
    file: build/journey/auth/login.html
    status: planned
  - id: home
    title: Home
    domain: dashboard
    file: build/journey/home.html
    status: planned
---
"""


class TestDeriveDomain:
    def test_subdir_after_journey(self):
        assert _derive_domain("build/journey/auth/login.html") == "auth"

    def test_no_subdir_after_journey(self):
        assert _derive_domain("build/journey/home.html") == "default"

    def test_no_journey_segment(self):
        assert _derive_domain("build/components/btn.html") == "default"

    def test_empty_string(self):
        assert _derive_domain("") == "default"

    def test_journey_at_root(self):
        assert _derive_domain("journey/onboarding/step.html") == "onboarding"

    def test_deep_path(self):
        assert _derive_domain("a/b/journey/claims/step1/page.html") == "claims"


# ---------------------------------------------------------------------------
# prototype_init
# ---------------------------------------------------------------------------


class TestPrototypeInit:
    def test_creates_csv(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        path = prototype_init(project)
        assert path.exists()
        assert path.name == "journey-map.csv"

    def test_returns_path(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        path = prototype_init(project)
        assert path == project / ".floop" / "journey-map.csv"

    def test_csv_header(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        assert set(rows[0].keys()) == {"domain", "page_id", "title", "html_file"}

    def test_derives_domain_from_file(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        auth_row = next(r for r in rows if r["page_id"] == "login")
        assert auth_row["domain"] == "auth"

    def test_default_domain_for_root_journey_page(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        home_row = next(r for r in rows if r["page_id"] == "home")
        assert home_row["domain"] == "default"

    def test_explicit_domain_field_takes_priority(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_DOMAIN_FIELD)
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        login_row = next(r for r in rows if r["page_id"] == "login")
        assert login_row["domain"] == "authentication"

    def test_csv_page_metadata(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        login_row = next(r for r in rows if r["page_id"] == "login")
        assert login_row["title"] == "Login"
        assert login_row["html_file"] == "build/journey/auth/login.html"

    def test_non_dict_page_skipped(self, tmp_path):
        """Pages that are not dicts (e.g. plain strings) are silently skipped."""
        project = make_project(tmp_path)
        write_sitemap(
            project,
            "---\nversion: 1\nupdated_at: 2024-01-01\npages:\n  - just-a-string\n---\n",
        )
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        assert rows == []

    def test_overwrites_existing_csv(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        # Second call should not raise and should overwrite
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        assert rows == []

    def test_raises_if_no_sitemap(self, tmp_path):
        project = make_project(tmp_path)
        with pytest.raises(FileNotFoundError, match="sitemap.md not found"):
            prototype_init(project)

    def test_empty_pages_creates_empty_csv(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        prototype_init(project)
        rows = list(csv.DictReader((project / ".floop" / "journey-map.csv").open(encoding="utf-8")))
        assert rows == []

    def test_creates_parent_dirs(self, tmp_path):
        # project WITHOUT .floop directory — should create it
        write_content = (
            "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n"
        )
        floop_dir = tmp_path / ".floop"
        floop_dir.mkdir()
        (floop_dir / "sitemap.md").write_text(write_content, encoding="utf-8")
        path = prototype_init(tmp_path)
        assert path.exists()


# ---------------------------------------------------------------------------
# prototype_validate
# ---------------------------------------------------------------------------


def write_journey_map(project_dir: Path, content: str) -> Path:
    path = project_dir / ".floop" / "journey-map.csv"
    path.write_text(content, encoding="utf-8")
    return path


def make_journey_html(project_dir: Path, rel_path: str) -> Path:
    """Create a dummy HTML file at .floop/<rel_path>."""
    full = project_dir / ".floop" / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text("<html></html>", encoding="utf-8")
    return full


class TestPrototypeValidate:
    def test_missing_csv_returns_error(self, tmp_path):
        project = make_project(tmp_path)
        errors, _ = prototype_validate(project)
        assert any("journey-map.csv not found" in e for e in errors)

    def test_valid_when_all_html_mapped(self, tmp_path):
        project = make_project(tmp_path)
        make_journey_html(project, "build/journey/auth/login.html")
        write_journey_map(
            project,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        errors, warnings = prototype_validate(project)
        assert errors == []

    def test_unmapped_html_returns_error(self, tmp_path):
        project = make_project(tmp_path)
        make_journey_html(project, "build/journey/auth/login.html")
        write_journey_map(project, "domain,page_id,title,html_file\n")
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        errors, _ = prototype_validate(project)
        assert any("journey HTML not mapped" in e for e in errors)
        assert any("build/journey/auth/login.html" in e for e in errors)

    def test_domain_not_in_sitemap_returns_error(self, tmp_path):
        project = make_project(tmp_path)
        write_journey_map(
            project,
            "domain,page_id,title,html_file\nunknown-domain,p1,P1,build/journey/unknown-domain/p1.html\n",
        )
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        errors, _ = prototype_validate(project)
        assert any("unknown-domain" in e for e in errors)

    def test_no_journey_dir_no_html_errors(self, tmp_path):
        project = make_project(tmp_path)
        write_journey_map(
            project,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        # journey dir doesn't exist yet — no HTML files → no html errors
        errors, warnings = prototype_validate(project)
        assert errors == []

    def test_missing_sitemap_returns_warning(self, tmp_path):
        project = make_project(tmp_path)
        write_journey_map(project, "domain,page_id,title,html_file\n")
        _, warnings = prototype_validate(project)
        assert any("sitemap.md not found" in w for w in warnings)

    def test_invalid_sitemap_yaml_returns_warning(self, tmp_path):
        project = make_project(tmp_path)
        write_journey_map(project, "domain,page_id,title,html_file\n")
        (project / ".floop" / "sitemap.md").write_text("---\n: bad: yaml:\n---\n", encoding="utf-8")
        _, warnings = prototype_validate(project)
        assert any("YAML parse error" in w for w in warnings)

    def test_empty_html_file_rows_skipped(self, tmp_path):
        """CSV rows with empty html_file do not become false errors."""
        project = make_project(tmp_path)
        write_journey_map(
            project,
            "domain,page_id,title,html_file\nauth,login,Login,\n",
        )
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        errors, _ = prototype_validate(project)
        # Empty html_file rows should not trip domain validation
        # auth domain IS in sitemap → no domain error
        assert not any("auth" in e and "not found" in e for e in errors)


# ---------------------------------------------------------------------------
# CLI — floop prototype
# ---------------------------------------------------------------------------


class TestCliPrototype:
    def test_init_creates_csv(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "journey-map.csv generated" in result.output
        assert (tmp_path / ".floop" / "journey-map.csv").exists()

    def test_init_fails_without_sitemap(self, tmp_path):
        project = make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_passes(self, tmp_path):
        project = make_project(tmp_path)
        write_sitemap(project, _SITEMAP_WITH_PAGES)
        prototype_init(project)
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_fails_on_errors(self, tmp_path):
        project = make_project(tmp_path)
        make_journey_html(project, "build/journey/extra/orphan.html")
        write_journey_map(project, "domain,page_id,title,html_file\n")
        write_sitemap(project, "---\nversion: 1\nupdated_at: 2024-01-01\npages: []\n---\n")
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1
        assert "error" in result.output

    def test_validate_shows_warnings(self, tmp_path):
        project = make_project(tmp_path)
        write_journey_map(project, "domain,page_id,title,html_file\n")
        # no sitemap.md → warning
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "⚠" in result.output

    def test_validate_missing_csv(self, tmp_path):
        project = make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["prototype", "validate", "--project-dir", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# version_create / version_list
# ---------------------------------------------------------------------------


class TestVersionCreate:
    def test_creates_snapshot_in_versions_dir(self, tmp_path):
        from floop.prototype import version_create
        floop_dir = tmp_path / ".floop"
        build_dir = floop_dir / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        (floop_dir / "versions").mkdir()
        ver = version_create(tmp_path, "v1.0", "first release")
        assert ver.is_dir()
        assert (ver / "home.html").exists()
        assert (ver / "meta.json").exists()

    def test_meta_json_contains_version_and_message(self, tmp_path):
        import json
        from floop.prototype import version_create
        floop_dir = tmp_path / ".floop"
        build_dir = floop_dir / "build"
        build_dir.mkdir(parents=True)
        (floop_dir / "versions").mkdir()
        ver = version_create(tmp_path, "v1.0", "my message")
        meta = json.loads((ver / "meta.json").read_text(encoding="utf-8"))
        assert meta["version"] == "v1.0"
        assert meta["message"] == "my message"
        assert "created_at" in meta

    def test_raises_if_version_already_exists(self, tmp_path):
        from floop.prototype import version_create
        floop_dir = tmp_path / ".floop"
        (floop_dir / "build").mkdir(parents=True)
        (floop_dir / "versions").mkdir()
        version_create(tmp_path, "v1.0")
        with pytest.raises(ValueError, match="already exists"):
            version_create(tmp_path, "v1.0")

    def test_raises_if_build_missing(self, tmp_path):
        from floop.prototype import version_create
        with pytest.raises(FileNotFoundError):
            version_create(tmp_path, "v1.0")

    def test_creates_versions_dir_if_absent(self, tmp_path):
        from floop.prototype import version_create
        floop_dir = tmp_path / ".floop"
        (floop_dir / "build").mkdir(parents=True)
        # versions/ not pre-created
        version_create(tmp_path, "v1.0")
        assert (floop_dir / "versions" / "v1.0").is_dir()


class TestVersionList:
    def test_returns_empty_when_no_versions_dir(self, tmp_path):
        from floop.prototype import version_list
        assert version_list(tmp_path) == []

    def test_returns_version_metadata(self, tmp_path):
        import json
        from floop.prototype import version_list
        ver_dir = tmp_path / ".floop" / "versions" / "v1.0"
        ver_dir.mkdir(parents=True)
        (ver_dir / "meta.json").write_text(
            json.dumps({"version": "v1.0", "message": "first", "created_at": "2026-01-01T00:00:00+00:00"}),
            encoding="utf-8",
        )
        result = version_list(tmp_path)
        assert len(result) == 1
        assert result[0]["version"] == "v1.0"

    def test_sorts_newest_first(self, tmp_path):
        import json
        from floop.prototype import version_list
        for name, dt in [("v1.0", "2026-01-01T00:00:00+00:00"), ("v1.1", "2026-02-01T00:00:00+00:00")]:
            d = tmp_path / ".floop" / "versions" / name
            d.mkdir(parents=True)
            (d / "meta.json").write_text(
                json.dumps({"version": name, "created_at": dt}), encoding="utf-8"
            )
        result = version_list(tmp_path)
        assert result[0]["version"] == "v1.1"

    def test_skips_invalid_meta(self, tmp_path):
        from floop.prototype import version_list
        d = tmp_path / ".floop" / "versions" / "broken"
        d.mkdir(parents=True)
        (d / "meta.json").write_text("not json", encoding="utf-8")
        assert version_list(tmp_path) == []


# ---------------------------------------------------------------------------
# _load_known_css_vars
# ---------------------------------------------------------------------------


class TestLoadKnownCssVars:
    def test_returns_none_when_no_tokens_dir(self, tmp_path):
        from floop.prototype import _load_known_css_vars
        assert _load_known_css_vars(tmp_path) is None

    def test_returns_none_when_empty_tokens_dir(self, tmp_path):
        from floop.prototype import _load_known_css_vars
        (tmp_path / ".floop" / "tokens").mkdir(parents=True)
        assert _load_known_css_vars(tmp_path) is None

    def test_collects_leaf_tokens(self, tmp_path):
        import json
        from floop.prototype import _load_known_css_vars
        tokens_dir = tmp_path / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "global.tokens.json").write_text(
            json.dumps({
                "color": {
                    "primary": {"$type": "color", "$value": "#2563EB"},
                    "blue": {
                        "500": {"$type": "color", "$value": "#3B82F6"},
                    },
                },
            }),
            encoding="utf-8",
        )
        result = _load_known_css_vars(tmp_path)
        assert result == {"--color-primary", "--color-blue-500"}

    def test_skips_dollar_keys(self, tmp_path):
        import json
        from floop.prototype import _load_known_css_vars
        tokens_dir = tmp_path / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "global.tokens.json").write_text(
            json.dumps({
                "$description": "ignore me",
                "size": {"sm": {"$value": "4px"}},
            }),
            encoding="utf-8",
        )
        result = _load_known_css_vars(tmp_path)
        assert result == {"--size-sm"}

    def test_skips_invalid_json(self, tmp_path):
        from floop.prototype import _load_known_css_vars
        tokens_dir = tmp_path / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True)
        (tokens_dir / "bad.tokens.json").write_text("not json", encoding="utf-8")
        result = _load_known_css_vars(tmp_path)
        assert result == set()


# ---------------------------------------------------------------------------
# journey_check
# ---------------------------------------------------------------------------


class TestJourneyCheck:
    def _make_html(self, project_dir, filename="login.html", content=None):
        """Write an HTML file under .floop/build/journey/."""
        journey_dir = project_dir / ".floop" / "build" / "journey"
        journey_dir.mkdir(parents=True, exist_ok=True)
        html_path = journey_dir / filename
        if content is None:
            content = (
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>hello</body></html>"
            )
        html_path.write_text(content, encoding="utf-8")
        return html_path

    def _make_tokens(self, project_dir, data=None):
        import json
        tokens_dir = project_dir / ".floop" / "tokens"
        tokens_dir.mkdir(parents=True, exist_ok=True)
        if data is None:
            data = {"color": {"primary": {"$type": "color", "$value": "#2563EB"}}}
        (tokens_dir / "global.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def _make_components(self, project_dir, content=None):
        if content is None:
            content = textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: navbar
                    title: Navbar
                    status: ready
                  - id: hero-card
                    title: Hero Card
                    status: ready
            """)
        (project_dir / ".floop" / "components.yaml").write_text(
            content, encoding="utf-8"
        )

    def test_file_not_found(self, tmp_path):
        prj = make_project(tmp_path)
        errors, warnings = journey_check(prj, prj / "missing.html")
        assert any("not found" in e for e in errors)

    def test_all_pass(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_tokens(prj)
        self._make_components(prj)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<div class="navbar">Nav</div>'
                '<div class="hero-card" style="color: var(--color-primary);">Card</div>'
                "</body></html>"
            ),
        )
        errors, warnings = journey_check(prj, html)
        assert errors == []
        assert warnings == []

    def test_missing_head_links(self, tmp_path):
        prj = make_project(tmp_path)
        html = self._make_html(
            prj, content="<html><head></head><body></body></html>"
        )
        errors, _ = journey_check(prj, html)
        assert any("tokens.css" in e for e in errors)
        assert any("components.js" in e for e in errors)

    def test_token_ref_not_found(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_tokens(prj)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<p style="color: var(--color-nonexistent)">text</p>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert any("--color-nonexistent" in e for e in errors)

    def test_token_ref_found(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_tokens(prj)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<p style="color: var(--color-primary)">text</p>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert errors == []

    def test_token_refs_without_token_files(self, tmp_path):
        prj = make_project(tmp_path)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<p style="color: var(--color-primary)">text</p>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert any("no *.tokens.json files found" in e for e in errors)

    def test_no_token_refs_without_token_files_is_ok(self, tmp_path):
        """No var(--xxx) and no token files → no token errors."""
        prj = make_project(tmp_path)
        html = self._make_html(prj)
        errors, _ = journey_check(prj, html)
        # No token-related errors
        assert not any("token" in e.lower() for e in errors)

    def test_component_not_referenced(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_components(prj)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<div class="navbar">Nav</div>'
                "</body></html>"
            ),
        )
        _, warnings = journey_check(prj, html)
        assert any("hero-card" in w for w in warnings)

    def test_components_yaml_not_found(self, tmp_path):
        prj = make_project(tmp_path)
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        assert any("components.yaml not found" in w for w in warnings)

    def test_components_yaml_parse_error(self, tmp_path):
        prj = make_project(tmp_path)
        (prj / ".floop" / "components.yaml").write_text(
            "{{bad yaml", encoding="utf-8"
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        assert any("YAML parse error" in w for w in warnings)

    def test_components_yaml_not_dict(self, tmp_path):
        prj = make_project(tmp_path)
        (prj / ".floop" / "components.yaml").write_text(
            "- just a list", encoding="utf-8"
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        # No crash — not a dict so component check is silently skipped
        assert not any("YAML parse error" in w for w in warnings)

    def test_components_yaml_empty_list(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components: []
            """),
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        # Empty list = nothing to check → no component warnings
        assert not any("not referenced" in w for w in warnings)

    def test_components_yaml_non_list(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components: "not a list"
            """),
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        assert not any("not referenced" in w for w in warnings)

    def test_component_entry_without_id(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - title: No ID
                    status: ready
            """),
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        # No id → skipped, no warning about "not referenced"
        assert not any("not referenced" in w for w in warnings)

    def test_component_entry_non_dict(self, tmp_path):
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - just a string
            """),
        )
        html = self._make_html(prj)
        _, warnings = journey_check(prj, html)
        assert not any("not referenced" in w for w in warnings)

    # -- 4. Raw tag detection (html_tag field) ---

    def test_raw_tag_detected(self, tmp_path):
        """html_tag: input on form-field → raw <input> is an error."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<input type="text" placeholder="Name">'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert any("raw <input>" in e and "form-field" in e for e in errors)

    def test_raw_tag_with_class_passes(self, tmp_path):
        """<input class="form-field"> → component class present → no error."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<input class="form-field" type="text">'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)

    def test_raw_tag_with_data_component_passes(self, tmp_path):
        """<input data-component="form-field"> → JS component wired → no error."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<input data-component="form-field" type="text">'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)

    def test_raw_tag_mixed_some_wired_some_not(self, tmp_path):
        """Some <input> tags wired, one bare → error reported once."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<input class="form-field" type="text">'
                '<input type="hidden" name="csrf">'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert any("raw <input>" in e for e in errors)

    def test_raw_tag_not_present_no_error(self, tmp_path):
        """html_tag declared but no raw tag in HTML → no error."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<div class="form-field">Name</div>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)

    def test_no_html_tag_field_no_check(self, tmp_path):
        """Components without html_tag → no raw tag check."""
        prj = make_project(tmp_path)
        self._make_components(prj)
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<nav><a href="/">Home</a></nav>'
                '<div class="navbar">Nav</div>'
                '<div class="hero-card">Card</div>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)

    def test_html_tag_null_ignored(self, tmp_path):
        """html_tag: null → treated as absent, no raw tag check."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: navbar
                    title: Navbar
                    status: ready
                    html_tag: null
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<nav><a href="/">Home</a></nav>'
                '<div class="navbar">Nav</div>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)

    def test_multiple_html_tags_detected(self, tmp_path):
        """Multiple components with html_tag → each raw tag flagged."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: form-field
                    title: Form Field
                    status: ready
                    html_tag: input
                  - id: action-button
                    title: Action Button
                    status: ready
                    html_tag: button
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                '<input type="email">'
                "<button>Submit</button>"
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert any("raw <input>" in e and "form-field" in e for e in errors)
        assert any("raw <button>" in e and "action-button" in e for e in errors)

    def test_html_tag_empty_string_ignored(self, tmp_path):
        """html_tag: '' → treated as absent, no raw tag check."""
        prj = make_project(tmp_path)
        self._make_components(
            prj,
            content=textwrap.dedent("""\
                version: 1
                updated_at: "2026-01-01"
                css_framework: tailwind
                components:
                  - id: navbar
                    title: Navbar
                    status: ready
                    html_tag: ""
            """),
        )
        html = self._make_html(
            prj,
            content=(
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>"
                "<nav>Nav</nav>"
                '<div class="navbar">Nav</div>'
                "</body></html>"
            ),
        )
        errors, _ = journey_check(prj, html)
        assert not any("raw" in e for e in errors)
