"""floop review upload support.

Builds a ZIP archive from a saved floop version snapshot and uploads it to
floop-server's ZIP upload API.
"""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable


DEFAULT_SERVER_URL = "https://floop-server.vercel.app"
CONFIG_KEY = "review"
ENV_FILE_NAME = "floop.env"
PROJECT_PLACEHOLDER = "<project-key>"
API_KEY_PLACEHOLDER = "flp_..."


class ReviewError(RuntimeError):
    """Raised for user-actionable review upload failures."""


def normalize_server_url(server_url: str) -> str:
    """Return a clean server URL without trailing slashes."""
    normalized = server_url.strip().rstrip("/")
    if not normalized:
        raise ReviewError("Server URL cannot be empty.")
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ReviewError("Server URL must start with http:// or https://.")
    return normalized


def load_floop_config(project_dir: Path) -> dict:
    """Load .floop/config.json, returning an empty mapping if absent."""
    config_path = project_dir / ".floop" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewError(f"Invalid .floop/config.json: {exc}") from exc


def save_review_config(project_dir: Path, server_url: str, project_key: str) -> Path:
    """Persist non-secret review settings in .floop/config.json."""
    floop_dir = project_dir / ".floop"
    if not floop_dir.exists():
        raise ReviewError(".floop/ not found. Run 'floop init' first.")

    config = load_floop_config(project_dir)
    config[CONFIG_KEY] = {
        "server_url": normalize_server_url(server_url),
        "project_key": project_key.strip(),
    }
    config_path = floop_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path


def load_floop_env(project_dir: Path) -> dict[str, str]:
    """Load .floop/floop.env as simple KEY=VALUE pairs."""
    env_path = project_dir / ".floop" / ENV_FILE_NAME
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ReviewError(f"Invalid .floop/{ENV_FILE_NAME} line {line_number}: expected KEY=VALUE.")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ReviewError(f"Invalid .floop/{ENV_FILE_NAME} line {line_number}: empty key.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def get_review_env(project_dir: Path) -> tuple[str | None, str | None, str | None]:
    """Return review settings from .floop/floop.env."""
    values = load_floop_env(project_dir)
    server_url = values.get("FLOOP_SERVER_URL") or values.get("FLOOP_REVIEW_SERVER_URL")
    project_key = values.get("FLOOP_PROJECT_KEY")
    api_key = values.get("FLOOP_API_KEY")
    return (
        str(server_url) if server_url and not is_review_placeholder(server_url) else None,
        str(project_key) if project_key and not is_review_placeholder(project_key) else None,
        str(api_key) if api_key and not is_review_placeholder(api_key) else None,
    )


def is_review_placeholder(value: str) -> bool:
    """Return whether an env value is a setup placeholder, not a real credential."""
    stripped = value.strip()
    return not stripped or stripped in {PROJECT_PLACEHOLDER, API_KEY_PLACEHOLDER} or stripped.startswith("<")


def ensure_review_env_gitignored(project_dir: Path) -> None:
    """Ensure .floop/floop.env is ignored by git because it stores secrets."""
    floop_dir = project_dir / ".floop"
    gitignore_path = floop_dir / ".gitignore"
    ignore_line = f"/{ENV_FILE_NAME}"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if ignore_line in lines or ENV_FILE_NAME in lines:
            return
        suffix = "" if content.endswith("\n") or not content else "\n"
        gitignore_path.write_text(f"{content}{suffix}{ignore_line}\n", encoding="utf-8")
        return
    gitignore_path.write_text(f"# Local floop secrets\n{ignore_line}\n", encoding="utf-8")


def save_review_env(project_dir: Path, server_url: str, project_key: str, api_key: str) -> Path:
    """Persist review settings in .floop/floop.env for non-interactive uploads."""
    floop_dir = project_dir / ".floop"
    if not floop_dir.exists():
        raise ReviewError(".floop/ not found. Run 'floop init' first.")

    normalized_server = normalize_server_url(server_url)
    clean_project = project_key.strip()
    clean_api_key = api_key.strip()
    if not clean_project:
        raise ReviewError("Project key cannot be empty.")
    if not clean_api_key:
        raise ReviewError("API key cannot be empty.")

    env_path = floop_dir / ENV_FILE_NAME
    env_path.write_text(
        "# floop review settings. Keep this file private.\n"
        f"FLOOP_SERVER_URL={normalized_server}\n"
        f"FLOOP_PROJECT_KEY={clean_project}\n"
        f"FLOOP_API_KEY={clean_api_key}\n",
        encoding="utf-8",
    )
    ensure_review_env_gitignored(project_dir)
    return env_path


def write_review_env_template(
    project_dir: Path,
    *,
    server_url: str | None = None,
    project_key: str | None = None,
    api_key: str | None = None,
) -> Path:
    """Create or update .floop/floop.env with known values and placeholders."""
    floop_dir = project_dir / ".floop"
    if not floop_dir.exists():
        raise ReviewError(".floop/ not found. Run 'floop init' first.")

    existing = load_floop_env(project_dir)
    selected_server = (
        server_url
        or existing.get("FLOOP_SERVER_URL")
        or existing.get("FLOOP_REVIEW_SERVER_URL")
        or DEFAULT_SERVER_URL
    )
    selected_project = (
        project_key
        or existing.get("FLOOP_PROJECT_KEY")
        or PROJECT_PLACEHOLDER
    )
    selected_api_key = api_key or existing.get("FLOOP_API_KEY") or API_KEY_PLACEHOLDER

    env_path = floop_dir / ENV_FILE_NAME
    env_path.write_text(
        "# floop review settings. Keep this file private.\n"
        "# Fill FLOOP_PROJECT_KEY and FLOOP_API_KEY before running floop review.\n"
        f"FLOOP_SERVER_URL={normalize_server_url(selected_server)}\n"
        f"FLOOP_PROJECT_KEY={selected_project}\n"
        f"FLOOP_API_KEY={selected_api_key}\n",
        encoding="utf-8",
    )
    ensure_review_env_gitignored(project_dir)
    return env_path


def get_review_config(project_dir: Path) -> tuple[str | None, str | None]:
    """Return configured (server_url, project_key), if present."""
    config = load_floop_config(project_dir)
    review_config = config.get(CONFIG_KEY) if isinstance(config, dict) else None
    if not isinstance(review_config, dict):
        return None, None
    server_url = review_config.get("server_url")
    project_key = review_config.get("project_key")
    return (
        str(server_url) if server_url else None,
        str(project_key) if project_key else None,
    )


def resolve_review_source(project_dir: Path, version: str | None) -> tuple[Path, str]:
    """Resolve the directory and label to upload.

    If *version* is omitted, the latest named snapshot is used. Passing
    ``trunk`` explicitly uploads the current .floop/build directory.
    """
    floop_dir = project_dir / ".floop"
    if not floop_dir.exists():
        raise ReviewError(".floop/ not found. Run 'floop init' first.")

    if version == "trunk":
        source_dir = floop_dir / "build"
        if not source_dir.exists():
            raise ReviewError(".floop/build/ not found. Run 'floop init' first.")
        return source_dir, "trunk"

    selected_version = version
    if not selected_version:
        from floop.prototype import version_list

        versions = version_list(project_dir)
        if not versions:
            raise ReviewError(
                "No saved versions found. Run 'floop version create <name>' before review, "
                "or pass '--version trunk' to upload the current build."
            )
        selected_version = versions[0]["version"]

    source_dir = floop_dir / "versions" / selected_version
    if not source_dir.exists():
        raise ReviewError(f"Version '{selected_version}' not found in .floop/versions/.")
    return source_dir, selected_version


def create_review_archive(source_dir: Path) -> bytes:
    """Create a ZIP archive from a review source directory."""
    if not source_dir.exists():
        raise ReviewError(f"Review source not found: {source_dir}")

    files = [path for path in sorted(source_dir.rglob("*")) if path.is_file()]
    files = [path for path in files if path.name not in {".DS_Store"}]
    files = [path for path in files if path.relative_to(source_dir).as_posix() != "index.html"]
    if not files:
        raise ReviewError("Review source is empty; generate preview artifacts first.")

    html_files = [path for path in files if path.suffix.lower() == ".html"]
    if not html_files:
        raise ReviewError("Review source has no HTML files; run 'floop preview' or build a journey first.")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            arcname = path.relative_to(source_dir).as_posix()
            archive.write(path, arcname)
    return buffer.getvalue()


def _encode_multipart(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    boundary: str,
) -> bytes:
    body = BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        body.write(value.encode())
        body.write(b"\r\n")

    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    )
    body.write(b"Content-Type: application/zip\r\n\r\n")
    body.write(file_bytes)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    return body.getvalue()


def _read_response_json(response) -> dict:
    raw = response.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"Server returned invalid JSON: {raw[:200]}") from exc


def _extract_error_message(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text or "Request failed."
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or data)
    if error:
        return str(error)
    return text or "Request failed."


def _request_json(
    *,
    server_url: str,
    path: str,
    api_key: str,
    method: str = "GET",
    payload: dict | None = None,
    timeout: int = 60,
    opener: Callable | None = None,
) -> dict:
    """Send an authenticated floop-server JSON request."""
    if not api_key.strip():
        raise ReviewError("API key cannot be empty.")

    data = None
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        normalize_server_url(server_url) + path,
        data=data,
        method=method,
        headers=headers,
    )
    open_request = opener or urllib.request.urlopen

    try:
        response = open_request(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        message = _extract_error_message(exc.read())
        raise ReviewError(f"floop-server request failed ({exc.code}): {message}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"Could not reach floop-server: {exc.reason}") from exc

    try:
        return _read_response_json(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def list_review_projects(
    *,
    server_url: str,
    api_key: str,
    timeout: int = 60,
    opener: Callable | None = None,
) -> list[dict]:
    """Return projects owned by the API key user."""
    data = _request_json(
        server_url=server_url,
        path="/api/v1/me/projects",
        api_key=api_key,
        timeout=timeout,
        opener=opener,
    )
    projects = data.get("projects")
    if not isinstance(projects, list):
        raise ReviewError("Server returned invalid projects payload.")
    return [project for project in projects if isinstance(project, dict)]


def create_review_project(
    *,
    server_url: str,
    api_key: str,
    name: str,
    slug: str | None = None,
    timeout: int = 60,
    opener: Callable | None = None,
) -> dict:
    """Create a floop-server project and return it."""
    clean_name = name.strip()
    if not clean_name:
        raise ReviewError("Project name cannot be empty.")
    payload = {"name": clean_name}
    if slug and slug.strip():
        payload["slug"] = slug.strip()

    data = _request_json(
        server_url=server_url,
        path="/api/v1/me/projects",
        api_key=api_key,
        method="POST",
        payload=payload,
        timeout=timeout,
        opener=opener,
    )
    project = data.get("project")
    if not isinstance(project, dict) or not project.get("id"):
        raise ReviewError("Server returned invalid created project payload.")
    return project


def absolute_server_url(server_url: str, path_or_url: str | None) -> str | None:
    """Convert a server-relative response URL into an absolute URL."""
    if not path_or_url:
        return None
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return normalize_server_url(server_url) + "/" + path_or_url.lstrip("/")


def upload_review(
    *,
    server_url: str,
    project_key: str,
    api_key: str,
    archive_bytes: bytes,
    version_label: str,
    timeout: int = 60,
    opener: Callable | None = None,
) -> dict:
    """Upload an archive to floop-server and return response data."""
    if not project_key.strip():
        raise ReviewError("Project key cannot be empty.")
    if not api_key.strip():
        raise ReviewError("API key cannot be empty.")

    normalized_server = normalize_server_url(server_url)
    encoded_project = urllib.parse.quote(project_key.strip(), safe="")
    upload_url = f"{normalized_server}/api/v1/me/projects/{encoded_project}/uploads/zip"
    boundary = f"floop-{secrets.token_hex(12)}"
    body = _encode_multipart(
        {"versionLabel": version_label},
        "archive",
        f"{version_label}.zip",
        archive_bytes,
        boundary,
    )
    request = urllib.request.Request(
        upload_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    open_request = opener or urllib.request.urlopen

    try:
        response = open_request(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        message = _extract_error_message(exc.read())
        raise ReviewError(f"Upload failed ({exc.code}): {message}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"Could not reach floop-server: {exc.reason}") from exc

    try:
        data = _read_response_json(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()

    data["previewUrl"] = absolute_server_url(normalized_server, data.get("previewUrl"))
    data["shareUrl"] = absolute_server_url(normalized_server, data.get("shareUrl"))
    if not data.get("shareUrl"):
        raise ReviewError("Upload succeeded but server did not return a shareUrl.")
    return data


def list_review_versions(
    *,
    server_url: str,
    project_key: str,
    api_key: str,
    timeout: int = 30,
) -> list[dict]:
    """List all versions for a project from floop-server."""
    if not project_key.strip():
        raise ReviewError("Project key cannot be empty.")
    if not api_key.strip():
        raise ReviewError("API key cannot be empty.")

    normalized_server = normalize_server_url(server_url)
    encoded_project = urllib.parse.quote(project_key.strip(), safe="")
    url = f"{normalized_server}/api/v1/me/projects/{encoded_project}/versions"

    response_data = _request_json(
        url=url,
        method="GET",
        api_key=api_key,
        timeout=timeout,
    )

    if "items" not in response_data:
        raise ReviewError("Server response missing 'items' field.")

    items = response_data["items"]
    if not isinstance(items, list):
        raise ReviewError("Server response 'items' is not a list.")

    # Convert relative URLs to absolute
    for item in items:
        if isinstance(item, dict):
            item["previewUrl"] = absolute_server_url(normalized_server, item.get("previewUrl"))
            item["shareUrl"] = absolute_server_url(normalized_server, item.get("shareUrl"))

    return items


def get_review_comments(
    *,
    server_url: str,
    project_key: str,
    version_id: str,
    api_key: str,
    timeout: int = 30,
) -> list[dict]:
    """Fetch all comments for a specific version from floop-server."""
    if not project_key.strip():
        raise ReviewError("Project key cannot be empty.")
    if not version_id.strip():
        raise ReviewError("Version ID cannot be empty.")
    if not api_key.strip():
        raise ReviewError("API key cannot be empty.")

    normalized_server = normalize_server_url(server_url)
    encoded_project = urllib.parse.quote(project_key.strip(), safe="")
    encoded_version = urllib.parse.quote(version_id.strip(), safe="")
    url = f"{normalized_server}/api/v1/me/projects/{encoded_project}/versions/{encoded_version}/comments"

    response_data = _request_json(
        url=url,
        method="GET",
        api_key=api_key,
        timeout=timeout,
    )

    if "items" not in response_data:
        raise ReviewError("Server response missing 'items' field.")

    items = response_data["items"]
    if not isinstance(items, list):
        raise ReviewError("Server response 'items' is not a list.")

    return items
