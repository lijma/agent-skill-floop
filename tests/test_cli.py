"""Tests for floop CLI commands."""

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from floop import __version__
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
        assert __version__ in result.output

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
        content = gitignore.read_text(encoding="utf-8")
        assert "build/" in content
        assert "/floop.env" in content

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
        """preview starts without writing index.html into build/."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            runner.invoke(main, ["preview", "--project-dir", str(project)])
            assert not (project / ".floop" / "build" / "index.html").exists()

    def test_preview_uses_runtime_handler(self, runner, project):
        """preview passes a virtual index handler to HTTPServer."""
        build_dir = project / ".floop" / "build"
        (build_dir / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")

        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            runner.invoke(main, ["preview", "--project-dir", str(project)])
            handler = mock_server_cls.call_args.args[1]
            assert handler.__name__ == "PreviewRequestHandler"
            assert not (build_dir / "index.html").exists()

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
        """--version flag is accepted by the runtime handler."""
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
            handler = mock_server_cls.call_args.args[1]
            assert handler.__name__ == "PreviewRequestHandler"
            assert not (build_dir / "index.html").exists()

    def test_preview_url_uses_root_path(self, runner, project):
        """URL printed points at the virtual preview index."""
        with patch("http.server.HTTPServer") as mock_server_cls:
            mock_server = mock_server_cls.return_value
            mock_server.serve_forever.side_effect = KeyboardInterrupt

            result = runner.invoke(main, ["preview", "--project-dir", str(project)])
            assert "http://127.0.0.1:" in result.output
            assert "/build/" not in result.output


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
# floop review
# ---------------------------------------------------------------------------


class TestReviewCommand:
    def _create_version(self, runner, project):
        build_dir = project / ".floop" / "build"
        journey_dir = build_dir / "journey"
        journey_dir.mkdir()
        (journey_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        runner.invoke(main, ["version", "create", "v1.0", "--project-dir", str(project)])

    def test_review_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["review", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert ".floop" in result.output

    def test_review_uploads_version(self, runner, project):
        self._create_version(runner, project)
        with patch("floop.review.upload_review") as mock_upload:
            mock_upload.return_value = {
                "projectId": "proj_1",
                "versionId": "ver_1",
                "status": "ready",
                "previewUrl": "https://server.example/p/ver_1",
                "shareUrl": "https://server.example/s/shr_1",
            }
            result = runner.invoke(
                main,
                [
                    "review",
                    "--server-url",
                    "https://server.example",
                    "--project-key",
                    "proj_1",
                    "--api-key",
                    "flp_secret",
                    "--version",
                    "v1.0",
                    "--project-dir",
                    str(project),
                ],
            )
        assert result.exit_code == 0
        assert "Review version uploaded" in result.output
        assert "https://server.example/s/shr_1" in result.output
        mock_upload.assert_called_once()
        config = json.loads((project / ".floop" / "config.json").read_text(encoding="utf-8"))
        assert "review" not in config
        env_content = (project / ".floop" / "floop.env").read_text(encoding="utf-8")
        assert "FLOOP_SERVER_URL=https://server.example" in env_content
        assert "FLOOP_PROJECT_KEY=proj_1" in env_content
        assert "FLOOP_API_KEY=flp_secret" in env_content

    def test_review_uses_floop_env_without_prompts(self, runner, project):
        self._create_version(runner, project)
        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://env.example\n"
            "FLOOP_PROJECT_KEY=proj_env\n"
            "FLOOP_API_KEY=flp_env_file\n",
            encoding="utf-8",
        )
        with patch("floop.review.upload_review") as mock_upload:
            mock_upload.return_value = {
                "projectId": "proj_env",
                "versionId": "ver_1",
                "status": "ready",
                "previewUrl": "https://env.example/p/ver_1",
                "shareUrl": "https://env.example/s/shr_1",
            }
            result = runner.invoke(
                main,
                ["review", "--version", "v1.0", "--project-dir", str(project)],
            )

        assert result.exit_code == 0
        assert "First-time floop review setup" not in result.output
        assert mock_upload.call_args.kwargs["server_url"] == "https://env.example"
        assert mock_upload.call_args.kwargs["project_key"] == "proj_env"
        assert mock_upload.call_args.kwargs["api_key"] == "flp_env_file"

    def test_review_accepts_project_key(self, runner, project):
        self._create_version(runner, project)
        with patch("floop.review.upload_review") as mock_upload:
            mock_upload.return_value = {
                "projectId": "proj_key",
                "versionId": "ver_1",
                "status": "ready",
                "previewUrl": "https://server.example/p/ver_1",
                "shareUrl": "https://server.example/s/shr_1",
            }
            result = runner.invoke(
                main,
                [
                    "review",
                    "--server-url",
                    "https://server.example",
                    "--project-key",
                    "proj_key",
                    "--api-key",
                    "flp_secret",
                    "--version",
                    "v1.0",
                    "--project-dir",
                    str(project),
                ],
            )

        assert result.exit_code == 0
        assert mock_upload.call_args.kwargs["project_key"] == "proj_key"

    def test_review_json_output_uses_env_api_key(self, runner, project, monkeypatch):
        self._create_version(runner, project)
        monkeypatch.setenv("FLOOP_API_KEY", "flp_env")
        with patch("floop.review.upload_review") as mock_upload:
            mock_upload.return_value = {
                "projectId": "proj_1",
                "versionId": "ver_1",
                "status": "ready",
                "previewUrl": "https://server.example/p/ver_1",
                "shareUrl": "https://server.example/s/shr_1",
            }
            result = runner.invoke(
                main,
                [
                    "review",
                    "--server-url",
                    "https://server.example",
                    "--project-key",
                    "proj_1",
                    "--json-output",
                    "--project-dir",
                    str(project),
                ],
            )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["shareUrl"] == "https://server.example/s/shr_1"
        assert mock_upload.call_args.kwargs["api_key"] == "flp_env"

    def test_review_missing_settings_creates_env_template(self, runner, project):
        self._create_version(runner, project)
        with patch("floop.review.upload_review") as mock_upload:
            result = runner.invoke(
                main,
                ["review", "--project-dir", str(project)],
            )
        assert result.exit_code == 0
        assert "setup required" in result.output
        assert "floop.env" in result.output
        assert "Missing: FLOOP_API_KEY, FLOOP_PROJECT_KEY" in result.output
        assert "NEXT: run 'floop review set' now" in result.output
        assert "not a build/upload failure" in result.output
        env_content = (
            project / ".floop" / "floop.env"
        ).read_text(encoding="utf-8")
        assert "FLOOP_PROJECT_KEY=<project-key>" in env_content
        assert "FLOOP_PROJECT_ID" not in env_content
        mock_upload.assert_not_called()

    def test_review_missing_settings_json_output_is_successful(self, runner, project):
        self._create_version(runner, project)
        with patch("floop.review.upload_review") as mock_upload:
            result = runner.invoke(
                main,
                ["review", "--json-output", "--project-dir", str(project)],
            )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["status"] == "setup_required"
        assert payload["uploaded"] is False
        assert payload["missing"] == ["FLOOP_API_KEY", "FLOOP_PROJECT_KEY"]
        assert payload["nextCommand"] == "floop review set"
        mock_upload.assert_not_called()

    def test_review_set_uses_single_project(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            mock_list.return_value = [
                {"id": "prj_1", "name": "Demo", "slug": "demo", "status": "active"}
            ]
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--server-url",
                    "https://server.example",
                    "--api-key",
                    "flp_secret",
                    "--project-dir",
                    str(project),
                ],
            )

        assert result.exit_code == 0
        assert "settings saved" in result.output
        assert "next: floop review --json-output" in result.output
        env_content = (project / ".floop" / "floop.env").read_text(encoding="utf-8")
        assert "FLOOP_SERVER_URL=https://server.example" in env_content
        assert "FLOOP_PROJECT_KEY=prj_1" in env_content
        assert "FLOOP_API_KEY=flp_secret" in env_content

    def test_review_set_creates_project_when_none_exists(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            with patch("floop.review.create_review_project") as mock_create:
                mock_list.return_value = []
                mock_create.return_value = {"id": "prj_new", "name": "New", "slug": "new"}
                result = runner.invoke(
                    main,
                    [
                        "review",
                        "set",
                        "--api-key",
                        "flp_secret",
                        "--project-name",
                        "New",
                        "--json-output",
                        "--project-dir",
                        str(project),
                    ],
                )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["projectKey"] == "prj_new"
        assert mock_create.call_args.kwargs["name"] == "New"

    def test_review_set_uses_project_dir_name_when_creating(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            with patch("floop.review.create_review_project") as mock_create:
                mock_list.return_value = []
                mock_create.return_value = {"id": "prj_new", "name": project.name, "slug": project.name}
                result = runner.invoke(
                    main,
                    [
                        "review",
                        "set",
                        "--api-key",
                        "flp_secret",
                        "--project-dir",
                        str(project),
                    ],
                )

        assert result.exit_code == 0
        assert mock_create.call_args.kwargs["name"] == project.name

    def test_review_set_selects_multiple_projects(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            mock_list.return_value = [
                {"id": "prj_1", "name": "One", "slug": "one", "status": "active"},
                {"id": "prj_2", "name": "Two", "slug": "two", "status": "active"},
            ]
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--api-key",
                    "flp_secret",
                    "--project-dir",
                    str(project),
                ],
                input="2\n",
            )

        assert result.exit_code == 0
        assert "Multiple floop projects found" in result.output
        assert "One (prj_1)" in result.output
        assert "Two (prj_2)" in result.output
        env_content = (project / ".floop" / "floop.env").read_text(encoding="utf-8")
        assert "FLOOP_PROJECT_KEY=prj_2" in env_content

    def test_review_set_rejects_unknown_project_key(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            mock_list.return_value = [
                {"id": "prj_1", "name": "One", "slug": "one", "status": "active"}
            ]
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--api-key",
                    "flp_secret",
                    "--project-key",
                    "prj_missing",
                    "--project-dir",
                    str(project),
                ],
            )

        assert result.exit_code != 0
        assert "Project key not found" in result.output

    def test_review_set_accepts_known_project_key(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            mock_list.return_value = [
                {"id": "prj_1", "name": "One", "slug": "one", "status": "active"}
            ]
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--api-key",
                    "flp_secret",
                    "--project-key",
                    "prj_1",
                    "--project-dir",
                    str(project),
                ],
            )

        assert result.exit_code == 0
        env_content = (project / ".floop" / "floop.env").read_text(encoding="utf-8")
        assert "FLOOP_PROJECT_KEY=prj_1" in env_content

    def test_review_set_prompts_for_api_key(self, runner, project):
        with patch("floop.review.list_review_projects") as mock_list:
            mock_list.return_value = [
                {"id": "prj_1", "name": "Demo", "slug": "demo", "status": "active"}
            ]
            result = runner.invoke(
                main,
                ["review", "set", "--project-dir", str(project)],
                input="flp_prompt\n",
            )

        assert result.exit_code == 0
        assert mock_list.call_args.kwargs["api_key"] == "flp_prompt"

    def test_review_set_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["review", "set", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert ".floop" in result.output

    def test_review_handles_upload_error(self, runner, project):
        self._create_version(runner, project)
        from floop.review import ReviewError

        with patch("floop.review.upload_review", side_effect=ReviewError("boom")):
            result = runner.invoke(
                main,
                [
                    "review",
                    "--server-url",
                    "https://server.example",
                    "--project-key",
                    "proj_1",
                    "--api-key",
                    "flp_secret",
                    "--project-dir",
                    str(project),
                ],
            )
        assert result.exit_code != 0
        assert "boom" in result.output


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


class TestFeedbackCommand:
    def test_feedback_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["feedback", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert ".floop/" in result.output

    def test_feedback_without_floop_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["feedback", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert ".floop/" in result.output

    def test_feedback_missing_config(self, runner, project):
        result = runner.invoke(main, ["feedback", "--project-dir", str(project)])
        assert result.exit_code == 0
        assert "Review settings not configured" in result.output
        assert "FLOOP_SERVER_URL" in result.output
        assert "floop review set" in result.output

    def test_feedback_missing_config_json(self, runner, project):
        result = runner.invoke(main, ["feedback", "--project-dir", str(project), "--json-output"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["error"] == "SETUP_REQUIRED"
        assert "FLOOP_SERVER_URL" in payload["missing"]

    def test_feedback_no_versions(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        with patch("floop.review.list_review_versions") as mock_list:
            mock_list.return_value = []

            result = runner.invoke(main, ["feedback", "--project-dir", str(project)])

        assert result.exit_code == 0
        assert "No versions found" in result.output
        assert "floop review" in result.output

    def test_feedback_no_versions_json(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        with patch("floop.review.list_review_versions") as mock_list:
            mock_list.return_value = []

            result = runner.invoke(main, ["feedback", "--project-dir", str(project), "--json-output"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "comments" in payload
        assert len(payload["comments"]) == 0
        assert "No versions found" in payload["message"]

    def test_feedback_shows_comments(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            }
        ]

        comments_data = [
            {
                "id": "cmt_1",
                "authorName": "Reviewer",
                "body": "Great work!",
                "status": "open",
                "priority": "medium",
            },
            {
                "id": "cmt_2",
                "authorName": "Designer",
                "body": "Change button color",
                "status": "open",
                "priority": "high",
            },
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            with patch("floop.review.get_review_comments") as mock_comments:
                mock_list.return_value = versions_data
                mock_comments.return_value = comments_data

                result = runner.invoke(main, ["feedback", "--project-dir", str(project)])

        assert result.exit_code == 0
        assert "Review Feedback for 'v1.0'" in result.output
        assert "Total comments: 2" in result.output
        assert "Open: 2" in result.output

    def test_feedback_json_output(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            }
        ]

        comments_data = [
            {
                "id": "cmt_1",
                "authorName": "Reviewer",
                "body": "Great work!",
                "status": "open",
                "priority": "medium",
            }
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            with patch("floop.review.get_review_comments") as mock_comments:
                mock_list.return_value = versions_data
                mock_comments.return_value = comments_data

                result = runner.invoke(
                    main,
                    ["feedback", "--project-dir", str(project), "--json-output"],
                )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["versionId"] == "ver_1"
        assert payload["versionLabel"] == "v1.0"
        assert payload["commentCount"] == 1
        assert len(payload["comments"]) == 1

    def test_feedback_with_specific_version(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            },
            {
                "versionId": "ver_2",
                "versionLabel": "v2.0",
                "status": "ready",
                "uploadedAt": "2026-05-09T00:00:00Z",
            }
        ]

        comments_data = [
            {
                "id": "cmt_1",
                "authorName": "Reviewer",
                "body": "Looks good!",
                "status": "open",
                "priority": "low",
            }
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            with patch("floop.review.get_review_comments") as mock_comments:
                mock_list.return_value = versions_data
                mock_comments.return_value = comments_data

                result = runner.invoke(
                    main,
                    ["feedback", "--version", "v1.0", "--project-dir", str(project)],
                )

        assert result.exit_code == 0
        assert "v1.0" in result.output
        assert "Total comments: 1" in result.output
        mock_comments.assert_called_once_with(
            server_url="https://server.example",
            project_key="proj_1",
            version_id="ver_1",
            api_key="flp_secret",
        )

    def test_feedback_version_not_found(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            },
            {
                "versionId": "ver_2",
                "status": "ready",
                "uploadedAt": "2026-05-07T00:00:00Z",
            }
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            mock_list.return_value = versions_data

            result = runner.invoke(
                main,
                ["feedback", "--version", "v2.0", "--project-dir", str(project)],
            )

        assert result.exit_code == 0
        assert "Version 'v2.0' not found" in result.output
        assert "Available versions:" in result.output
        assert "v1.0" in result.output
        assert "ver_2" in result.output

    def test_feedback_version_not_found_json(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            },
            {
                "versionId": "ver_2",
                "status": "ready",
                "uploadedAt": "2026-05-07T00:00:00Z",
            }
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            mock_list.return_value = versions_data

            result = runner.invoke(
                main,
                ["feedback", "--version", "v2.0", "--project-dir", str(project), "--json-output"],
            )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["error"] == "VERSION_NOT_FOUND"
        assert "v1.0" in payload["availableVersions"]
        assert "ver_2" in payload["availableVersions"]

    def test_feedback_handles_review_error(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        with patch("floop.review.list_review_versions") as mock_list:
            from floop.review import ReviewError
            mock_list.side_effect = ReviewError("API error")

            result = runner.invoke(
                main,
                ["feedback", "--project-dir", str(project)],
            )

        assert result.exit_code != 0
        assert "API error" in result.output

    def test_feedback_handles_review_error_json(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        with patch("floop.review.list_review_versions") as mock_list:
            from floop.review import ReviewError
            mock_list.side_effect = ReviewError("API error")

            result = runner.invoke(
                main,
                ["feedback", "--project-dir", str(project), "--json-output"],
            )

        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["error"] == "FEEDBACK_FAILED"
        assert "API error" in payload["message"]

    def test_feedback_no_comments_yet(self, runner, project):
        from unittest.mock import patch

        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=proj_1\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        versions_data = [
            {
                "versionId": "ver_1",
                "versionLabel": "v1.0",
                "status": "ready",
                "uploadedAt": "2026-05-08T00:00:00Z",
            }
        ]

        with patch("floop.review.list_review_versions") as mock_list:
            with patch("floop.review.get_review_comments") as mock_comments:
                mock_list.return_value = versions_data
                mock_comments.return_value = []

                result = runner.invoke(main, ["feedback", "--project-dir", str(project)])

        assert result.exit_code == 0
        assert "No comments yet for version 'v1.0'" in result.output
        assert "Share the review link with reviewers" in result.output
