"""Tests for floop CLI commands."""

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from floop.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project(tmp_path):
    """A tmp directory with .floop/ initialized."""
    floop_dir = tmp_path / ".floop"
    floop_dir.mkdir()
    (floop_dir / "build").mkdir()
    (floop_dir / "tokens").mkdir()
    config = {"version": "0.1.0"}
    (floop_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# floop --version / --help
# ---------------------------------------------------------------------------


class TestMainGroup:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "floop" in result.output
        assert "init" in result.output
        assert "enable" in result.output
        assert "token" in result.output


# ---------------------------------------------------------------------------
# floop init
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_creates_floop_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "✓" in result.output
        assert (tmp_path / ".floop").is_dir()
        assert (tmp_path / ".floop" / "config.json").exists()
        assert (tmp_path / ".floop" / "build").is_dir()
        assert (tmp_path / ".floop" / "tokens").is_dir()
        assert (tmp_path / ".floop" / "versions").is_dir()

    def test_init_skips_if_exists(self, runner, project):
        result = runner.invoke(main, ["init", "--project-dir", str(project)])
        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_init_writes_gitignore(self, runner, tmp_path):
        runner.invoke(main, ["init", "--project-dir", str(tmp_path)])
        gitignore = tmp_path / ".floop" / ".gitignore"
        assert gitignore.exists()
        assert "build/" in gitignore.read_text(encoding="utf-8")

    def test_init_config_has_version(self, runner, tmp_path):
        runner.invoke(main, ["init", "--project-dir", str(tmp_path)])
        config = json.loads(
            (tmp_path / ".floop" / "config.json").read_text(encoding="utf-8")
        )
        assert "version" in config


# ---------------------------------------------------------------------------
# floop enable
# ---------------------------------------------------------------------------


class TestEnableCommand:
    def test_enable_copilot(self, runner, tmp_path):
        result = runner.invoke(
            main, ["enable", "copilot", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output
        skills_dir = tmp_path / ".github" / "skills"
        assert skills_dir.is_dir()
        # Should have at least 1 skill
        skill_dirs = list(skills_dir.iterdir())
        assert len(skill_dirs) >= 1

    def test_enable_cursor(self, runner, tmp_path):
        result = runner.invoke(
            main, ["enable", "cursor", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        rules_dir = tmp_path / ".cursor" / "rules"
        assert rules_dir.is_dir()
        mdc_files = list(rules_dir.glob("*.mdc"))
        assert len(mdc_files) >= 1

    def test_enable_claude(self, runner, tmp_path):
        result = runner.invoke(
            main, ["enable", "claude", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        skills_dir = tmp_path / ".claude" / "skills"
        assert skills_dir.is_dir()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_enable_invalid_agent(self, runner, tmp_path):
        result = runner.invoke(
            main, ["enable", "invalid", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# floop token init
# ---------------------------------------------------------------------------


class TestTokenInitCommand:
    def test_token_init_creates_files(self, runner, project):
        result = runner.invoke(
            main, ["token", "init", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output
        tokens_dir = project / ".floop" / "tokens"
        assert (tokens_dir / "global.tokens.json").exists()
        assert (tokens_dir / "semantic.tokens.json").exists()
        assert (tokens_dir / "component.tokens.json").exists()

    def test_token_init_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(
            main, ["token", "init", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code != 0
        assert "floop init" in result.output

    def test_token_init_skips_if_exists(self, runner, project):
        # First init
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        # Second init without --force
        result = runner.invoke(
            main, ["token", "init", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "already exist" in result.output

    def test_token_init_force_overwrites(self, runner, project):
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        # Modify a file
        f = project / ".floop" / "tokens" / "global.tokens.json"
        f.write_text('{"modified": true}', encoding="utf-8")
        # Force overwrite
        result = runner.invoke(
            main, ["token", "init", "--force", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "modified" not in data


# ---------------------------------------------------------------------------
# floop token validate
# ---------------------------------------------------------------------------


class TestTokenValidateCommand:
    def test_validate_valid_tokens(self, runner, project):
        # Init tokens then validate
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        result = runner.invoke(
            main, ["token", "validate", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output or "valid" in result.output.lower()

    def test_validate_json_output(self, runner, project):
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        result = runner.invoke(
            main,
            ["token", "validate", "--json-output", "--project-dir", str(project)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "stats" in data
        assert data["valid"] is True

    def test_validate_no_tokens(self, runner, project):
        result = runner.invoke(
            main, ["token", "validate", "--project-dir", str(project)]
        )
        assert result.exit_code == 1  # errors → exit 1
        assert "NO_TOKEN_FILES" in result.output

    def test_validate_shows_errors(self, runner, project):
        tokens_dir = project / ".floop" / "tokens"
        bad = {"x": {"$type": "badType", "$value": "y"}}
        (tokens_dir / "bad.tokens.json").write_text(
            json.dumps(bad), encoding="utf-8"
        )
        result = runner.invoke(
            main, ["token", "validate", "--project-dir", str(project)]
        )
        assert result.exit_code == 1  # errors → exit 1
        assert "INVALID_TYPE" in result.output

    def test_validate_shows_warnings(self, runner, project):
        tokens_dir = project / ".floop" / "tokens"
        minimal = {"custom": {"$type": "color", "$value": "#000"}}
        (tokens_dir / "min.tokens.json").write_text(
            json.dumps(minimal), encoding="utf-8"
        )
        result = runner.invoke(
            main, ["token", "validate", "--project-dir", str(project)]
        )
        assert "MISSING_RECOMMENDED" in result.output

    def test_validate_json_output_with_errors(self, runner, project):
        tokens_dir = project / ".floop" / "tokens"
        (tokens_dir / "broken.tokens.json").write_text("{bad json", encoding="utf-8")
        result = runner.invoke(
            main,
            ["token", "validate", "--json-output", "--project-dir", str(project)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is False
        assert len(data["errors"]) > 0


# ---------------------------------------------------------------------------
# floop token (group help)
# ---------------------------------------------------------------------------


class TestTokenGroup:
    def test_token_help(self, runner):
        result = runner.invoke(main, ["token", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "validate" in result.output
        assert "view" in result.output
        assert "DTCG" in result.output


# ---------------------------------------------------------------------------
# floop token view
# ---------------------------------------------------------------------------


class TestTokenViewCommand:
    def test_view_generates_html(self, runner, project):
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        result = runner.invoke(
            main, ["token", "view", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output
        assert (project / ".floop" / "build" / "tokens" / "design-tokens.html").exists()

    def test_view_without_floop_dir(self, runner, tmp_path):
        # Remove .floop so tokens dir doesn't exist
        result = runner.invoke(
            main, ["token", "view", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code != 0

    def test_view_no_token_files(self, runner, project):
        # .floop/tokens/ exists but is empty
        result = runner.invoke(
            main, ["token", "view", "--project-dir", str(project)]
        )
        assert result.exit_code != 0

    def test_view_output_path(self, runner, project):
        runner.invoke(main, ["token", "init", "--project-dir", str(project)])
        result = runner.invoke(
            main, ["token", "view", "--project-dir", str(project)]
        )
        assert "design-tokens.html" in result.output


# ---------------------------------------------------------------------------
# floop preview
# ---------------------------------------------------------------------------


class TestPreviewCommand:
    def test_preview_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(
            main, ["preview", "--project-dir", str(tmp_path)]
        )
        assert result.exit_code != 0

    def test_preview_help(self, runner):
        result = runner.invoke(main, ["preview", "--help"])
        assert result.exit_code == 0
        assert "preview" in result.output.lower()
        assert "port" in result.output.lower()

    def test_preview_starts_server(self, runner, project):
        """Test that preview starts a server, showing the correct URL."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            result = runner.invoke(
                main, ["preview", "--project-dir", str(project)]
            )
            assert result.exit_code == 0
            assert "floop preview server" in result.output
            assert "127.0.0.1" in result.output
            mock_server.serve_forever.assert_called_once()
            mock_server.server_close.assert_called_once()

    def test_preview_shows_token_link(self, runner, project):
        """preview generates index.html in build/ on each run."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            runner.invoke(main, ["preview", "--project-dir", str(project)])
            assert (project / ".floop" / "build" / "index.html").exists()

    def test_preview_shows_prototype_links(self, runner, project):
        """preview index.html includes nav entries for files in build/."""
        build_dir = project / ".floop" / "build"
        (build_dir / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")

        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            runner.invoke(main, ["preview", "--project-dir", str(project)])
            index_html = (build_dir / "index.html").read_text(encoding="utf-8")
            assert "design-tokens.html" in index_html
            assert "home.html" in index_html

    def test_preview_custom_port(self, runner, project):
        """Test --port option is accepted."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            result = runner.invoke(
                main, ["preview", "--port", "0", "--project-dir", str(project)]
            )
            assert result.exit_code == 0

    def test_preview_version_flag(self, runner, project):
        """--version flag is accepted and persists to index.html."""
        build_dir = project / ".floop" / "build"
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        versions_dir = project / ".floop" / "versions" / "v1.0"
        versions_dir.mkdir(parents=True)
        import json as _json
        (versions_dir / "meta.json").write_text(
            _json.dumps({"version": "v1.0", "message": "first", "created_at": "2026-01-01T00:00:00+00:00"}),
            encoding="utf-8",
        )
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            result = runner.invoke(
                main, ["preview", "--version", "v1.0", "--project-dir", str(project)]
            )
            assert result.exit_code == 0
            index_html = (build_dir / "index.html").read_text(encoding="utf-8")
            assert '"v1.0"' in index_html

    def test_preview_url_uses_build_path(self, runner, project):
        """URL printed includes /build/ (server root is .floop/)."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            result = runner.invoke(main, ["preview", "--project-dir", str(project)])
            assert "/build/" in result.output


# ---------------------------------------------------------------------------
# floop version
# ---------------------------------------------------------------------------


class TestVersionCommand:
    def test_version_create_without_floop(self, runner, tmp_path):
        result = runner.invoke(main, ["version", "create", "v1.0", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert ".floop/" in result.output

    def test_version_create_success(self, runner, project):
        (project / ".floop" / "build" / "home.html").write_text("<html></html>", encoding="utf-8")
        result = runner.invoke(
            main, ["version", "create", "v1.0", "-m", "first release", "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output
        assert (project / ".floop" / "versions" / "v1.0").is_dir()

    def test_version_create_duplicate_fails(self, runner, project):
        (project / ".floop" / "build" / "home.html").write_text("<html></html>", encoding="utf-8")
        runner.invoke(main, ["version", "create", "v1.0", "--project-dir", str(project)])
        result = runner.invoke(main, ["version", "create", "v1.0", "--project-dir", str(project)])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_version_list_empty(self, runner, project):
        result = runner.invoke(main, ["version", "list", "--project-dir", str(project)])
        assert result.exit_code == 0
        assert "No versions found" in result.output

    def test_version_list_shows_versions(self, runner, project):
        (project / ".floop" / "build" / "home.html").write_text("<html></html>", encoding="utf-8")
        runner.invoke(main, ["version", "create", "v1.0", "-m", "first", "--project-dir", str(project)])
        result = runner.invoke(main, ["version", "list", "--project-dir", str(project)])
        assert result.exit_code == 0
        assert "v1.0" in result.output
        assert "first" in result.output

    def test_version_list_no_message(self, runner, project):
        (project / ".floop" / "build" / "home.html").write_text("<html></html>", encoding="utf-8")
        runner.invoke(main, ["version", "create", "v1.0", "--project-dir", str(project)])
        result = runner.invoke(main, ["version", "list", "--project-dir", str(project)])
        assert result.exit_code == 0
        assert "v1.0" in result.output


# ---------------------------------------------------------------------------
# floop journey check
# ---------------------------------------------------------------------------


class TestJourneyCheckCommand:
    def _write_html(self, project, name="login.html", content=None):
        journey_dir = project / ".floop" / "build" / "journey"
        journey_dir.mkdir(parents=True, exist_ok=True)
        html_path = journey_dir / name
        if content is None:
            content = (
                "<html><head>"
                '<link rel="stylesheet" href="../tokens/tokens.css">'
                '<script src="../components/components.js" defer></script>'
                "</head><body>hello</body></html>"
            )
        html_path.write_text(content, encoding="utf-8")
        return html_path

    def test_journey_check_without_floop(self, runner, tmp_path):
        html = tmp_path / "page.html"
        html.write_text("<html></html>", encoding="utf-8")
        result = runner.invoke(
            main, ["journey", "check", str(html), "--project-dir", str(tmp_path)]
        )
        assert result.exit_code != 0
        assert ".floop/" in result.output

    def test_journey_check_success(self, runner, project):
        html = self._write_html(project)
        result = runner.invoke(
            main, ["journey", "check", str(html), "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "✓" in result.output

    def test_journey_check_errors(self, runner, project):
        html = self._write_html(
            project, content="<html><head></head><body></body></html>"
        )
        result = runner.invoke(
            main, ["journey", "check", str(html), "--project-dir", str(project)]
        )
        assert result.exit_code != 0
        assert "✗" in result.output
        assert "tokens.css" in result.output

    def test_journey_check_shows_warnings(self, runner, project):
        html = self._write_html(project)
        # No components.yaml → warning
        result = runner.invoke(
            main, ["journey", "check", str(html), "--project-dir", str(project)]
        )
        assert result.exit_code == 0
        assert "⚠" in result.output
