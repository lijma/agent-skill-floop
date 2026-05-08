"""Tests for floop.review."""

import json
import urllib.error
import zipfile
from io import BytesIO

import pytest

from floop.review import (
    ReviewError,
    _extract_error_message,
    absolute_server_url,
    create_review_project,
    create_review_archive,
    get_review_comments,
    get_review_env,
    get_review_config,
    is_review_placeholder,
    list_review_projects,
    list_review_versions,
    load_floop_env,
    load_floop_config,
    normalize_server_url,
    resolve_review_source,
    save_review_env,
    save_review_config,
    upload_review,
    write_review_env_template,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")

    def close(self):
        self.closed = True


def make_project(tmp_path):
    floop_dir = tmp_path / ".floop"
    (floop_dir / "build").mkdir(parents=True)
    (floop_dir / "versions" / "v1.0").mkdir(parents=True)
    (floop_dir / "config.json").write_text('{"version":"0.1.0"}', encoding="utf-8")
    (floop_dir / "versions" / "v1.0" / "journey").mkdir()
    (floop_dir / "versions" / "v1.0" / "journey" / "home.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    (floop_dir / "versions" / "v1.0" / "meta.json").write_text(
        json.dumps(
            {
                "version": "v1.0",
                "message": "first",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


class TestReviewConfig:
    def test_normalize_server_url(self):
        assert normalize_server_url(" https://example.com/// ") == "https://example.com"

    def test_normalize_rejects_bad_url(self):
        with pytest.raises(ReviewError, match="http"):
            normalize_server_url("example.com")

    def test_normalize_rejects_empty_url(self):
        with pytest.raises(ReviewError, match="empty"):
            normalize_server_url("   ")

    def test_load_missing_config_returns_empty(self, tmp_path):
        assert load_floop_config(tmp_path) == {}

    def test_load_invalid_config_raises(self, tmp_path):
        floop_dir = tmp_path / ".floop"
        floop_dir.mkdir()
        (floop_dir / "config.json").write_text("{bad", encoding="utf-8")
        with pytest.raises(ReviewError, match="Invalid"):
            load_floop_config(tmp_path)

    def test_save_and_read_review_config(self, tmp_path):
        project = make_project(tmp_path)
        path = save_review_config(project, "https://server.example/", "proj_1")
        assert path.exists()
        assert get_review_config(project) == ("https://server.example", "proj_1")

    def test_load_floop_env_parses_values(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "floop.env").write_text(
            "# local review settings\n"
            "FLOOP_SERVER_URL='https://server.example/'\n"
            "FLOOP_PROJECT_KEY=proj_key\n"
            "FLOOP_API_KEY=flp_secret\n",
            encoding="utf-8",
        )

        assert load_floop_env(project)["FLOOP_API_KEY"] == "flp_secret"
        assert get_review_env(project) == (
            "https://server.example/",
            "proj_key",
            "flp_secret",
        )

    def test_get_review_env_ignores_placeholders(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://server.example\n"
            "FLOOP_PROJECT_KEY=<project-key>\n"
            "FLOOP_API_KEY=flp_...\n",
            encoding="utf-8",
        )

        assert get_review_env(project) == ("https://server.example", None, None)

    def test_is_review_placeholder(self):
        assert is_review_placeholder("<project-key>") is True
        assert is_review_placeholder("flp_...") is True
        assert is_review_placeholder("proj_123") is False

    def test_load_floop_env_rejects_invalid_lines(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "floop.env").write_text("FLOOP_API_KEY\n", encoding="utf-8")

        with pytest.raises(ReviewError, match="line 1"):
            load_floop_env(project)

    def test_load_floop_env_rejects_empty_key(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "floop.env").write_text("=flp_secret\n", encoding="utf-8")

        with pytest.raises(ReviewError, match="empty key"):
            load_floop_env(project)

    def test_save_review_env_writes_private_settings(self, tmp_path):
        project = make_project(tmp_path)
        path = save_review_env(project, "https://server.example/", "proj_1", "flp_secret")

        content = path.read_text(encoding="utf-8")
        assert "FLOOP_SERVER_URL=https://server.example" in content
        assert "FLOOP_PROJECT_KEY=proj_1" in content
        assert "FLOOP_API_KEY=flp_secret" in content
        assert "/floop.env" in (project / ".floop" / ".gitignore").read_text(encoding="utf-8")

    def test_save_review_env_appends_gitignore_once(self, tmp_path):
        project = make_project(tmp_path)
        gitignore = project / ".floop" / ".gitignore"
        gitignore.write_text("build/\n", encoding="utf-8")

        save_review_env(project, "https://server.example", "proj_1", "flp_secret")
        save_review_env(project, "https://server.example", "proj_1", "flp_secret")

        content = gitignore.read_text(encoding="utf-8")
        assert content.count("/floop.env") == 1

    def test_save_review_env_requires_floop_dir(self, tmp_path):
        with pytest.raises(ReviewError, match="floop init"):
            save_review_env(tmp_path, "https://server.example", "proj_1", "flp_secret")

    def test_save_review_env_rejects_empty_project(self, tmp_path):
        project = make_project(tmp_path)
        with pytest.raises(ReviewError, match="Project key"):
            save_review_env(project, "https://server.example", " ", "flp_secret")

    def test_save_review_env_rejects_empty_api_key(self, tmp_path):
        project = make_project(tmp_path)
        with pytest.raises(ReviewError, match="API key"):
            save_review_env(project, "https://server.example", "proj_1", " ")

    def test_write_review_env_template_uses_defaults(self, tmp_path):
        project = make_project(tmp_path)
        path = write_review_env_template(project)

        content = path.read_text(encoding="utf-8")
        assert "FLOOP_SERVER_URL=https://floop-server.vercel.app" in content
        assert "FLOOP_PROJECT_KEY=<project-key>" in content
        assert "FLOOP_API_KEY=flp_..." in content
        assert "/floop.env" in (project / ".floop" / ".gitignore").read_text(encoding="utf-8")

    def test_write_review_env_template_preserves_known_values(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "floop.env").write_text(
            "FLOOP_SERVER_URL=https://existing.example\n"
            "FLOOP_PROJECT_KEY=proj_existing\n",
            encoding="utf-8",
        )

        path = write_review_env_template(project, api_key="flp_secret")

        content = path.read_text(encoding="utf-8")
        assert "FLOOP_SERVER_URL=https://existing.example" in content
        assert "FLOOP_PROJECT_KEY=proj_existing" in content
        assert "FLOOP_API_KEY=flp_secret" in content

    def test_write_review_env_template_requires_floop_dir(self, tmp_path):
        with pytest.raises(ReviewError, match="floop init"):
            write_review_env_template(tmp_path)

    def test_save_config_requires_floop_dir(self, tmp_path):
        with pytest.raises(ReviewError, match="floop init"):
            save_review_config(tmp_path, "https://server.example", "proj_1")

    def test_get_review_config_without_review_key(self, tmp_path):
        project = make_project(tmp_path)
        assert get_review_config(project) == (None, None)


class TestReviewSource:
    def test_resolves_named_version(self, tmp_path):
        project = make_project(tmp_path)
        source, label = resolve_review_source(project, "v1.0")
        assert label == "v1.0"
        assert source.name == "v1.0"

    def test_resolves_latest_version(self, tmp_path):
        project = make_project(tmp_path)
        source, label = resolve_review_source(project, None)
        assert label == "v1.0"
        assert source == project / ".floop" / "versions" / "v1.0"

    def test_resolves_trunk(self, tmp_path):
        project = make_project(tmp_path)
        (project / ".floop" / "build" / "index.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        source, label = resolve_review_source(project, "trunk")
        assert label == "trunk"
        assert source.name == "build"

    def test_trunk_requires_build_dir(self, tmp_path):
        (tmp_path / ".floop").mkdir()
        with pytest.raises(ReviewError, match="build"):
            resolve_review_source(tmp_path, "trunk")

    def test_missing_floop_raises(self, tmp_path):
        with pytest.raises(ReviewError, match="floop init"):
            resolve_review_source(tmp_path, "trunk")

    def test_no_saved_versions_raises(self, tmp_path):
        floop_dir = tmp_path / ".floop"
        (floop_dir / "build").mkdir(parents=True)
        with pytest.raises(ReviewError, match="No saved versions"):
            resolve_review_source(tmp_path, None)

    def test_missing_named_version_raises(self, tmp_path):
        project = make_project(tmp_path)
        with pytest.raises(ReviewError, match="not found"):
            resolve_review_source(project, "v2.0")


class TestReviewArchive:
    def test_create_archive_includes_html(self, tmp_path):
        project = make_project(tmp_path)
        archive = create_review_archive(project / ".floop" / "versions" / "v1.0")
        assert b"journey/home.html" in archive

    def test_create_archive_requires_existing_source(self, tmp_path):
        with pytest.raises(ReviewError, match="not found"):
            create_review_archive(tmp_path / "missing")

    def test_create_archive_requires_files(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ReviewError, match="empty"):
            create_review_archive(empty)

    def test_create_archive_requires_html(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "style.css").write_text("body{}", encoding="utf-8")
        with pytest.raises(ReviewError, match="no HTML"):
            create_review_archive(source)

    def test_create_archive_excludes_root_index_when_present(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "journey").mkdir()
        (source / "index.html").write_text("<html>App</html>", encoding="utf-8")
        (source / "journey" / "home.html").write_text("<html></html>", encoding="utf-8")

        archive = create_review_archive(source)
        with zipfile.ZipFile(BytesIO(archive)) as zip_file:
            names = zip_file.namelist()
        assert "index.html" not in names
        assert "journey/home.html" in names

    def test_create_archive_requires_non_root_html(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "index.html").write_text("<html>App</html>", encoding="utf-8")

        with pytest.raises(ReviewError, match="empty"):
            create_review_archive(source)


class TestUploadReview:
    def test_extract_error_message_variants(self):
        assert _extract_error_message(b"plain failure") == "plain failure"
        assert _extract_error_message(b'{"error":{"code":"NOPE"}}') == "NOPE"
        assert _extract_error_message(b'{"error":"bad"}') == "bad"
        assert _extract_error_message(b"{}") == "{}"

    def test_absolute_server_url(self):
        assert absolute_server_url("https://server", "/s/1") == "https://server/s/1"
        assert absolute_server_url("https://server", "https://other/s/1") == "https://other/s/1"
        assert absolute_server_url("https://server", None) is None

    def test_list_review_projects_success(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            return FakeResponse({"projects": [{"id": "prj_1", "name": "Demo"}]})

        projects = list_review_projects(
            server_url="https://server.example/",
            api_key="flp_secret",
            timeout=7,
            opener=opener,
        )

        assert captured["url"] == "https://server.example/api/v1/me/projects"
        assert captured["headers"]["Authorization"] == "Bearer flp_secret"
        assert captured["timeout"] == 7
        assert projects == [{"id": "prj_1", "name": "Demo"}]

    def test_list_review_projects_rejects_invalid_payload(self):
        def opener(request, timeout):
            return FakeResponse({"projects": "bad"})

        with pytest.raises(ReviewError, match="invalid projects"):
            list_review_projects(
                server_url="https://server.example",
                api_key="flp_secret",
                opener=opener,
            )

    def test_list_review_projects_handles_http_error(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},
                BytesIO(b'{"error":{"message":"Invalid API key"}}'),
            )

        with pytest.raises(ReviewError, match="Invalid API key"):
            list_review_projects(
                server_url="https://server.example",
                api_key="flp_secret",
                opener=opener,
            )

    def test_list_review_projects_handles_url_error(self):
        def opener(request, timeout):
            raise urllib.error.URLError("offline")

        with pytest.raises(ReviewError, match="offline"):
            list_review_projects(
                server_url="https://server.example",
                api_key="flp_secret",
                opener=opener,
            )

    def test_list_review_projects_rejects_empty_api_key(self):
        with pytest.raises(ReviewError, match="API key"):
            list_review_projects(
                server_url="https://server.example",
                api_key=" ",
            )

    def test_create_review_project_success(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"project": {"id": "prj_new", "name": "Demo"}})

        project = create_review_project(
            server_url="https://server.example/",
            api_key="flp_secret",
            name="Demo",
            slug="demo",
            opener=opener,
        )

        assert captured["url"] == "https://server.example/api/v1/me/projects"
        assert captured["method"] == "POST"
        assert captured["headers"]["Content-type"] == "application/json"
        assert captured["body"] == {"name": "Demo", "slug": "demo"}
        assert project["id"] == "prj_new"

    def test_create_review_project_rejects_empty_name(self):
        with pytest.raises(ReviewError, match="Project name"):
            create_review_project(
                server_url="https://server.example",
                api_key="flp_secret",
                name=" ",
            )

    def test_create_review_project_rejects_invalid_payload(self):
        def opener(request, timeout):
            return FakeResponse({"project": {"name": "Demo"}})

        with pytest.raises(ReviewError, match="invalid created"):
            create_review_project(
                server_url="https://server.example",
                api_key="flp_secret",
                name="Demo",
                opener=opener,
            )

    def test_upload_review_success(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data
            return FakeResponse(
                {
                    "projectId": "proj_1",
                    "versionId": "ver_1",
                    "status": "ready",
                    "previewUrl": "/p/ver_1",
                    "shareUrl": "/s/shr_1",
                }
            )

        result = upload_review(
            server_url="https://server.example/",
            project_key="proj_1",
            api_key="flp_secret",
            archive_bytes=b"zip",
            version_label="v1.0",
            timeout=12,
            opener=opener,
        )
        assert captured["url"] == "https://server.example/api/v1/me/projects/proj_1/uploads/zip"
        assert captured["timeout"] == 12
        assert captured["headers"]["Authorization"] == "Bearer flp_secret"
        assert b'name="versionLabel"' in captured["body"]
        assert result["shareUrl"] == "https://server.example/s/shr_1"
        assert result["previewUrl"] == "https://server.example/p/ver_1"

    def test_upload_review_rejects_empty_project(self):
        with pytest.raises(ReviewError, match="Project key"):
            upload_review(
                server_url="https://server.example",
                project_key=" ",
                api_key="flp_secret",
                archive_bytes=b"zip",
                version_label="v1.0",
            )

    def test_upload_review_rejects_empty_api_key(self):
        with pytest.raises(ReviewError, match="API key"):
            upload_review(
                server_url="https://server.example",
                project_key="proj_1",
                api_key=" ",
                archive_bytes=b"zip",
                version_label="v1.0",
            )

    def test_upload_review_handles_http_error_json(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},
                BytesIO(b'{"error":{"message":"Invalid token"}}'),
            )

        with pytest.raises(ReviewError, match="Invalid token"):
            upload_review(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="flp_secret",
                archive_bytes=b"zip",
                version_label="v1.0",
                opener=opener,
            )

    def test_upload_review_handles_url_error(self):
        def opener(request, timeout):
            raise urllib.error.URLError("offline")

        with pytest.raises(ReviewError, match="offline"):
            upload_review(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="flp_secret",
                archive_bytes=b"zip",
                version_label="v1.0",
                opener=opener,
            )

    def test_upload_review_handles_invalid_json(self):
        def opener(request, timeout):
            return FakeResponse(b"not json")

        with pytest.raises(ReviewError, match="invalid JSON"):
            upload_review(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="flp_secret",
                archive_bytes=b"zip",
                version_label="v1.0",
                opener=opener,
            )

    def test_upload_review_requires_share_url(self):
        def opener(request, timeout):
            return FakeResponse({"previewUrl": "/p/ver_1"})

        with pytest.raises(ReviewError, match="shareUrl"):
            upload_review(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="flp_secret",
                archive_bytes=b"zip",
                version_label="v1.0",
                opener=opener,
            )

class TestReviewFeedback:
    def test_list_review_versions_returns_items(self):
        from unittest.mock import patch

        response_data = {
            "items": [
                {
                    "versionId": "ver_1",
                    "versionLabel": "v1.0",
                    "status": "ready",
                    "previewUrl": "/p/ver_1",
                    "shareUrl": "/s/shr_1",
                    "uploadedAt": "2026-05-08T00:00:00Z",
                },
                {
                    "versionId": "ver_2",
                    "versionLabel": "v2.0",
                    "status": "ready",
                    "previewUrl": "/p/ver_2",
                    "shareUrl": "/s/shr_2",
                    "uploadedAt": "2026-05-09T00:00:00Z",
                },
            ]
        }

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = response_data

            versions = list_review_versions(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="flp_secret",
            )

            assert len(versions) == 2
            assert versions[0]["versionId"] == "ver_1"
            assert versions[0]["previewUrl"] == "https://server.example/p/ver_1"
            assert versions[1]["versionId"] == "ver_2"

    def test_list_review_versions_rejects_missing_items(self):
        from unittest.mock import patch

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = {}

            with pytest.raises(ReviewError, match="missing 'items'"):
                list_review_versions(
                    server_url="https://server.example",
                    project_key="proj_1",
                    api_key="flp_secret",
                )

    def test_list_review_versions_rejects_non_list_items(self):
        from unittest.mock import patch

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = {"items": "not a list"}

            with pytest.raises(ReviewError, match="not a list"):
                list_review_versions(
                    server_url="https://server.example",
                    project_key="proj_1",
                    api_key="flp_secret",
                )

    def test_list_review_versions_rejects_empty_project_key(self):
        with pytest.raises(ReviewError, match="Project key cannot be empty"):
            list_review_versions(
                server_url="https://server.example",
                project_key="",
                api_key="flp_secret",
            )

    def test_list_review_versions_rejects_empty_api_key(self):
        with pytest.raises(ReviewError, match="API key cannot be empty"):
            list_review_versions(
                server_url="https://server.example",
                project_key="proj_1",
                api_key="",
            )

    def test_get_review_comments_returns_items(self):
        from unittest.mock import patch

        response_data = {
            "items": [
                {
                    "id": "cmt_1",
                    "versionId": "ver_1",
                    "authorName": "Reviewer",
                    "body": "Great work!",
                    "status": "open",
                    "priority": "medium",
                    "labels": ["copy"],
                    "createdAt": "2026-05-08T00:00:00Z",
                },
                {
                    "id": "cmt_2",
                    "versionId": "ver_1",
                    "authorName": "Designer",
                    "body": "Change the button color",
                    "status": "in_review",
                    "priority": "high",
                    "labels": ["bug", "layout"],
                    "createdAt": "2026-05-08T01:00:00Z",
                },
            ]
        }

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = response_data

            comments = get_review_comments(
                server_url="https://server.example",
                project_key="proj_1",
                version_id="ver_1",
                api_key="flp_secret",
            )

            assert len(comments) == 2
            assert comments[0]["id"] == "cmt_1"
            assert comments[0]["authorName"] == "Reviewer"
            assert comments[1]["id"] == "cmt_2"
            assert comments[1]["priority"] == "high"

    def test_get_review_comments_rejects_missing_items(self):
        from unittest.mock import patch

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = {}

            with pytest.raises(ReviewError, match="missing 'items'"):
                get_review_comments(
                    server_url="https://server.example",
                    project_key="proj_1",
                    version_id="ver_1",
                    api_key="flp_secret",
                )

    def test_get_review_comments_rejects_non_list_items(self):
        from unittest.mock import patch

        with patch("floop.review._request_json") as mock_request:
            mock_request.return_value = {"items": "not a list"}

            with pytest.raises(ReviewError, match="not a list"):
                get_review_comments(
                    server_url="https://server.example",
                    project_key="proj_1",
                    version_id="ver_1",
                    api_key="flp_secret",
                )

    def test_get_review_comments_rejects_empty_project_key(self):
        with pytest.raises(ReviewError, match="Project key cannot be empty"):
            get_review_comments(
                server_url="https://server.example",
                project_key="",
                version_id="ver_1",
                api_key="flp_secret",
            )

    def test_get_review_comments_rejects_empty_version_id(self):
        with pytest.raises(ReviewError, match="Version ID cannot be empty"):
            get_review_comments(
                server_url="https://server.example",
                project_key="proj_1",
                version_id="",
                api_key="flp_secret",
            )

    def test_get_review_comments_rejects_empty_api_key(self):
        with pytest.raises(ReviewError, match="API key cannot be empty"):
            get_review_comments(
                server_url="https://server.example",
                project_key="proj_1",
                version_id="ver_1",
                api_key="",
            )
