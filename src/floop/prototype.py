"""floop prototype management — PRD, Sitemap, Component DSL, Journey Map.

Handles initialization and validation of structured prototype artifacts:
  .floop/prd.md          — Product Requirements Document (YAML frontmatter + Markdown)
  .floop/sitemap.md      — Sitemap / page structure (YAML frontmatter + Markdown)
  .floop/components.yaml — Component library definition (pure YAML)
  .floop/journey-map.csv — Sitemap domain → HTML file mapping (domain, page_id, title, html_file)
"""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

PRD_TEMPLATE = """\
---
version: 1
updated_at: {date}
product: ""
target_users: []
core_flows: []
css_framework: tailwind
status: draft
---

## 产品背景

<!-- 描述这个产品要解决什么问题，目标是什么 -->

## 目标用户

<!-- 详细描述用户画像：谁在用，他们的目标是什么，当前痛点是什么 -->

## 核心价值主张

<!-- 为什么选择这个产品，而不是其他方案 -->

## 核心流程

<!-- 描述用户完成核心目标的主要操作流程 -->
"""

SITEMAP_TEMPLATE = """\
---
version: 1
updated_at: {date}
pages: []
---

<!-- Add pages in frontmatter, then describe each below -->

<!-- Example frontmatter:
pages:
  - id: home
    title: 首页
    file: build/journey/home.html
    status: planned
-->
"""

COMPONENT_TEMPLATE = """\
version: 1
updated_at: {date}
css_framework: tailwind
components: []

# Example component entry:
# - id: navbar
#   title: 导航栏
#   category: Navigation   # Actions | Navigation | Inputs | Containment | Feedback | Display
#   status: draft
#   html_tag: nav          # optional — native HTML tag this component replaces
#   variants:
#     - default
#     - scrolled
#   tokens:
#     background: color.surface
#     text: color.text
#   notes: Sticky header with responsive hamburger menu
"""

# ---------------------------------------------------------------------------
# YAML frontmatter parsing helpers
# ---------------------------------------------------------------------------

_VALID_PRD_STATUSES = frozenset({"draft", "confirmed"})
_VALID_PAGE_STATUSES = frozenset({"planned", "building", "built"})
_VALID_COMPONENT_STATUSES = frozenset({"draft", "built"})


def _parse_frontmatter(text: str) -> dict | None:
    """Parse YAML frontmatter between --- delimiters.

    Returns parsed dict or None if no valid frontmatter block found.
    Raises yaml.YAMLError if the frontmatter YAML is invalid.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    # Find second ---
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            fm_text = "\n".join(lines[1:i])
            return yaml.safe_load(fm_text) or {}
    return None


# ---------------------------------------------------------------------------
# PRD
# ---------------------------------------------------------------------------

def prd_init(project_dir: Path) -> Path:
    """Write .floop/prd.md template.

    Returns the path to the created file.
    Raises FileExistsError if the file already exists.
    """
    path = project_dir / ".floop" / "prd.md"
    if path.exists():
        raise FileExistsError(f"{path} already exists, use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        PRD_TEMPLATE.format(date=datetime.date.today().isoformat()),
        encoding="utf-8",
    )
    return path


def prd_validate(project_dir: Path) -> tuple[list[str], list[str]]:
    """Validate .floop/prd.md frontmatter.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    path = project_dir / ".floop" / "prd.md"
    if not path.exists():
        errors.append("prd.md not found — run 'floop prd init' to create it")
        return errors, warnings

    text = path.read_text(encoding="utf-8")

    try:
        fm = _parse_frontmatter(text)
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse error in prd.md frontmatter: {exc}")
        return errors, warnings

    if fm is None:
        errors.append("prd.md has no YAML frontmatter (expected --- block at top)")
        return errors, warnings

    # Required fields
    if "version" not in fm:
        errors.append("missing required field: version")
    if "updated_at" not in fm:
        errors.append("missing required field: updated_at")
    if "product" not in fm:
        errors.append("missing required field: product")
    elif not fm["product"]:
        errors.append("field 'product' must be a non-empty string")
    if "target_users" not in fm:
        errors.append("missing required field: target_users")
    elif not fm["target_users"]:
        errors.append("field 'target_users' must be a non-empty list")
    if "core_flows" not in fm:
        errors.append("missing required field: core_flows")
    elif not fm["core_flows"]:
        errors.append("field 'core_flows' must be a non-empty list")
    if "css_framework" not in fm:
        errors.append("missing required field: css_framework")
    if "status" not in fm:
        errors.append("missing required field: status")
    elif fm["status"] not in _VALID_PRD_STATUSES:
        errors.append(
            f"invalid status '{fm['status']}' — must be one of: "
            + ", ".join(sorted(_VALID_PRD_STATUSES))
        )

    # Warnings
    if fm.get("status") == "draft":
        warnings.append("PRD status is still 'draft' — confirm with user when ready")

    return errors, warnings


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------

def sitemap_init(project_dir: Path) -> Path:
    """Write .floop/sitemap.md template.

    Returns the path to the created file.
    Raises FileExistsError if the file already exists.
    """
    path = project_dir / ".floop" / "sitemap.md"
    if path.exists():
        raise FileExistsError(f"{path} already exists, use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        SITEMAP_TEMPLATE.format(date=datetime.date.today().isoformat()),
        encoding="utf-8",
    )
    return path


def sitemap_validate(project_dir: Path) -> tuple[list[str], list[str]]:
    """Validate .floop/sitemap.md frontmatter.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    path = project_dir / ".floop" / "sitemap.md"
    if not path.exists():
        errors.append("sitemap.md not found — run 'floop sitemap init' to create it")
        return errors, warnings

    text = path.read_text(encoding="utf-8")

    try:
        fm = _parse_frontmatter(text)
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse error in sitemap.md frontmatter: {exc}")
        return errors, warnings

    if fm is None:
        errors.append("sitemap.md has no YAML frontmatter (expected --- block at top)")
        return errors, warnings

    # Required top-level fields
    if "version" not in fm:
        errors.append("missing required field: version")
    if "updated_at" not in fm:
        errors.append("missing required field: updated_at")
    if "pages" not in fm:
        errors.append("missing required field: pages")
        return errors, warnings

    pages = fm["pages"]
    if not isinstance(pages, list) or len(pages) == 0:
        errors.append("field 'pages' must be a non-empty list")
        return errors, warnings

    seen_ids: set[str] = set()
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            errors.append(f"pages[{i}] must be a mapping (dict)")
            continue
        for field in ("id", "title", "file", "status"):
            if field not in page:
                errors.append(f"pages[{i}] missing required field: {field}")
        page_id = page.get("id")
        if page_id is not None:
            if page_id in seen_ids:
                errors.append(f"duplicate page id: '{page_id}'")
            else:
                seen_ids.add(page_id)
        status = page.get("status")
        if status is not None and status not in _VALID_PAGE_STATUSES:
            errors.append(
                f"pages[{i}] invalid status '{status}' — must be one of: "
                + ", ".join(sorted(_VALID_PAGE_STATUSES))
            )
        elif status == "built":
            file_path = page.get("file")
            floop_dir = project_dir / ".floop"
            if file_path and not (floop_dir / file_path).exists():
                warnings.append(
                    f"pages[{i}] (id={page_id!r}) status is 'built' but file not found: {file_path}"
                )

    return errors, warnings


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------

def component_init(project_dir: Path) -> Path:
    """Write .floop/components.yaml template.

    Returns the path to the created file.
    Raises FileExistsError if the file already exists.
    """
    path = project_dir / ".floop" / "components.yaml"
    if path.exists():
        raise FileExistsError(f"{path} already exists, use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        COMPONENT_TEMPLATE.format(date=datetime.date.today().isoformat()),
        encoding="utf-8",
    )
    return path


def component_validate(project_dir: Path) -> tuple[list[str], list[str]]:
    """Validate .floop/components.yaml.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    path = project_dir / ".floop" / "components.yaml"
    if not path.exists():
        errors.append(
            "components.yaml not found — run 'floop component init' to create it"
        )
        return errors, warnings

    text = path.read_text(encoding="utf-8")
    # Strip comment lines before parsing (YAML comments are fine, but we keep them)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse error in components.yaml: {exc}")
        return errors, warnings

    if not isinstance(data, dict):
        errors.append("components.yaml must be a YAML mapping at the top level")
        return errors, warnings

    for field in ("version", "updated_at", "css_framework", "components"):
        if field not in data:
            errors.append(f"missing required top-level field: {field}")

    components = data.get("components")
    if components is None:
        return errors, warnings

    if not isinstance(components, list):
        errors.append("field 'components' must be a list")
        return errors, warnings

    if len(components) == 0:
        warnings.append(
            "components list is empty — add component definitions to get the most out of floop"
        )
        return errors, warnings

    known_token_paths = _load_known_token_paths(project_dir)

    seen_ids: set[str] = set()
    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            errors.append(f"components[{i}] must be a mapping (dict)")
            continue
        for field in ("id", "title", "status"):
            if field not in comp:
                errors.append(f"components[{i}] missing required field: {field}")
        comp_id = comp.get("id")
        if comp_id is not None:
            if comp_id in seen_ids:
                errors.append(f"duplicate component id: '{comp_id}'")
            else:
                seen_ids.add(comp_id)
        status = comp.get("status")
        if status is not None and status not in _VALID_COMPONENT_STATUSES:
            errors.append(
                f"components[{i}] invalid status '{status}' — must be one of: "
                + ", ".join(sorted(_VALID_COMPONENT_STATUSES))
            )
        if not comp.get("tokens"):
            warnings.append(
                f"components[{i}] (id={comp.get('id', '?')!r}) has no tokens defined"
            )
        else:
            token_map = comp.get("tokens")
            if isinstance(token_map, dict) and known_token_paths is not None:
                for prop, token_path in token_map.items():
                    if isinstance(token_path, str) and token_path not in known_token_paths:
                        warnings.append(
                            f"components[{i}] (id={comp_id!r}) tokens.{prop}: "
                            f"'{token_path}' not found in any *.tokens.json file"
                        )

    return errors, warnings


def _load_known_token_paths(project_dir: Path) -> set[str] | None:
    """Return all dotted token paths from *.tokens.json files, or None if no files exist."""
    tokens_dir = project_dir / ".floop" / "tokens"
    if not tokens_dir.exists():
        return None
    files = list(tokens_dir.glob("*.tokens.json"))
    if not files:
        return None
    import json

    def _collect(data: dict, prefix: str = "") -> set[str]:
        paths: set[str] = set()
        for key, value in data.items():
            if key.startswith("$"):
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                paths.add(path)
                paths.update(_collect(value, path))
        return paths

    all_paths: set[str] = set()
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_paths.update(_collect(data))
        except Exception:
            pass
    return all_paths


# ---------------------------------------------------------------------------
# Journey Map
# ---------------------------------------------------------------------------

JOURNEY_MAP_FIELDS = ("domain", "page_id", "title", "html_file")


def _derive_domain(file_path: str) -> str:
    """Derive a domain name from a file path.

    Uses the first sub-directory after 'journey/' as the domain.
    Falls back to 'default' if no such sub-directory exists.

    >>> _derive_domain("build/journey/auth/login.html")
    'auth'
    >>> _derive_domain("build/journey/home.html")
    'default'
    >>> _derive_domain("")
    'default'
    """
    if not file_path:
        return "default"
    parts = Path(file_path).parts
    try:
        idx = next(i for i, p in enumerate(parts) if p == "journey")
        if idx + 2 < len(parts):
            return parts[idx + 1]
    except StopIteration:
        pass
    return "default"


def prototype_init(project_dir: Path) -> Path:
    """Create (or overwrite) .floop/journey-map.csv from sitemap.md pages.

    Each sitemap page becomes a row: domain is taken from the page's optional
    'domain' field; if absent it is derived from the file path via
    _derive_domain().  The CSV is always regenerated (idempotent).

    Returns the path to the written CSV file.
    Raises FileNotFoundError if sitemap.md does not exist.
    """
    sitemap_path = project_dir / ".floop" / "sitemap.md"
    if not sitemap_path.exists():
        raise FileNotFoundError(
            "sitemap.md not found — run 'floop sitemap init' to create it"
        )

    text = sitemap_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text) or {}

    rows: list[dict[str, str]] = []
    for page in fm.get("pages") or []:
        if not isinstance(page, dict):
            continue
        html_file = str(page.get("file") or "")
        domain = str(page.get("domain") or _derive_domain(html_file))
        rows.append(
            {
                "domain": domain,
                "page_id": str(page.get("id") or ""),
                "title": str(page.get("title") or ""),
                "html_file": html_file,
            }
        )

    csv_path = project_dir / ".floop" / "journey-map.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(JOURNEY_MAP_FIELDS))
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def prototype_validate(project_dir: Path) -> tuple[list[str], list[str]]:
    """Validate journey HTML files against journey-map.csv and sitemap.md.

    Two checks:
    1. Every HTML file under .floop/build/journey/ has a row in journey-map.csv.
    2. Every domain in journey-map.csv also appears as a derived domain in
       sitemap.md (pages).

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    csv_path = project_dir / ".floop" / "journey-map.csv"
    if not csv_path.exists():
        errors.append(
            "journey-map.csv not found — run 'floop prototype init' first"
        )
        return errors, warnings

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        csv_rows = list(reader)

    csv_html_files: set[str] = {row.get("html_file", "") for row in csv_rows}
    csv_domains: set[str] = {row.get("domain", "") for row in csv_rows}

    # Check 1 — every .floop/build/journey/**/*.html is in the CSV
    journey_dir = project_dir / ".floop" / "build" / "journey"
    if journey_dir.exists():
        for html_path in sorted(journey_dir.rglob("*.html")):
            rel = html_path.relative_to(project_dir / ".floop").as_posix()
            if rel not in csv_html_files:
                errors.append(
                    f"journey HTML not mapped in journey-map.csv: {rel}"
                )

    # Check 2 — every CSV domain appears as a derived domain in sitemap.md
    sitemap_path = project_dir / ".floop" / "sitemap.md"
    if not sitemap_path.exists():
        warnings.append(
            "sitemap.md not found — skipping domain existence check"
        )
    else:
        text = sitemap_path.read_text(encoding="utf-8")
        try:
            fm = _parse_frontmatter(text) or {}
        except yaml.YAMLError:
            warnings.append(
                "sitemap.md has YAML parse error — skipping domain existence check"
            )
            fm = {}

        sitemap_domains: set[str] = set()
        for page in fm.get("pages") or []:
            if isinstance(page, dict):
                html_file = str(page.get("file") or "")
                domain = str(page.get("domain") or _derive_domain(html_file))
                sitemap_domains.add(domain)

        for domain in sorted(csv_domains):
            if domain and domain not in sitemap_domains:
                errors.append(
                    f"domain '{domain}' in journey-map.csv not found in sitemap.md"
                )

    return errors, warnings


# ---------------------------------------------------------------------------
# Version management — trunk-based snapshots
# ---------------------------------------------------------------------------


def version_create(project_dir: Path, name: str, message: str = "") -> Path:
    """Snapshot .floop/build/ into .floop/versions/<name>/.

    Raises FileNotFoundError if .floop/build/ does not exist.
    Raises ValueError if a version with *name* already exists.
    Returns the created version directory.
    """
    import json
    import shutil

    floop_dir = project_dir / ".floop"
    build_dir = floop_dir / "build"
    versions_dir = floop_dir / "versions"

    if not build_dir.exists():
        raise FileNotFoundError(".floop/build/ not found. Run 'floop init' first.")

    versions_dir.mkdir(parents=True, exist_ok=True)
    version_dir = versions_dir / name

    if version_dir.exists():
        raise ValueError(f"Version '{name}' already exists.")

    shutil.copytree(str(build_dir), str(version_dir))

    meta = {
        "version": name,
        "message": message,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (version_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    return version_dir


def version_list(project_dir: Path) -> list[dict]:
    """Return version metadata dicts sorted by created_at descending.

    Each dict has keys: version, message, created_at.
    Returns an empty list if no versions exist.
    """
    import json

    versions_dir = project_dir / ".floop" / "versions"
    if not versions_dir.exists():
        return []

    results = []
    for meta_path in sorted(versions_dir.glob("*/meta.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results


# ---------------------------------------------------------------------------
# Journey backward check — token & component gap detection
# ---------------------------------------------------------------------------


def _load_known_css_vars(project_dir: Path) -> set[str] | None:
    """Return CSS variable names (``--xxx``) that ``tokens.css`` would contain.

    Walks ``*.tokens.json`` files, finds leaf token nodes (those with
    ``$value``), and converts their dotted path to the CSS variable name
    using the same convention as ``generate_tokens_css``:
    ``dotted.path`` → ``--dotted-path``.

    Returns ``None`` if no token files exist.
    """
    tokens_dir = project_dir / ".floop" / "tokens"
    if not tokens_dir.exists():
        return None
    files = list(tokens_dir.glob("*.tokens.json"))
    if not files:
        return None
    import json

    def _leaves(data: dict, prefix: str = "") -> set[str]:
        result: set[str] = set()
        for key, value in data.items():
            if key.startswith("$"):
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                if "$value" in value:
                    result.add("--" + path.replace(".", "-"))
                else:
                    result.update(_leaves(value, path))
        return result

    all_vars: set[str] = set()
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_vars.update(_leaves(data))
        except Exception:
            pass
    return all_vars


def journey_check(
    project_dir: Path, html_file: Path
) -> tuple[list[str], list[str]]:
    """Backward-check a journey HTML file for token and component gaps.

    Scans the HTML content for:

    1. **Head links** — ``tokens.css`` and ``components.js`` must be referenced.
    2. **Token references** — every ``var(--xxx)`` must map to a leaf token in
       ``*.tokens.json``.
    3. **Component coverage** — components defined in ``components.yaml`` but
       not referenced anywhere in the HTML are flagged as warnings.

    Returns ``(errors, warnings)``.
    """
    import re

    errors: list[str] = []
    warnings: list[str] = []

    if not html_file.exists():
        errors.append(f"HTML file not found: {html_file}")
        return errors, warnings

    content = html_file.read_text(encoding="utf-8")

    # -- 1. Head link checks ------------------------------------------------
    if "tokens.css" not in content:
        errors.append("missing <link> to tokens.css in <head>")
    if "components.js" not in content:
        errors.append("missing <script> for components.js in <head>")

    # -- 2. Token backward check --------------------------------------------
    token_refs = set(re.findall(r"var\((--[a-zA-Z0-9_-]+)", content))
    known_vars = _load_known_css_vars(project_dir)

    if token_refs and known_vars is None:
        errors.append(
            "HTML references CSS custom properties but no *.tokens.json files found"
        )
    elif known_vars is not None:
        for ref in sorted(token_refs):
            if ref not in known_vars:
                errors.append(f"token {ref} not found in any *.tokens.json")

    # -- 3. Component backward check ----------------------------------------
    comp_path = project_dir / ".floop" / "components.yaml"
    if not comp_path.exists():
        warnings.append(
            "components.yaml not found — skipping component check"
        )
    else:
        try:
            data = yaml.safe_load(comp_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            warnings.append(
                "components.yaml has YAML parse error — skipping component check"
            )
            data = None

        if isinstance(data, dict):
            components = data.get("components")
            if isinstance(components, list) and components:
                unused = []
                tag_map: dict[str, str] = {}  # html_tag -> component id
                for comp in components:
                    if isinstance(comp, dict):
                        cid = comp.get("id")
                        if cid and cid not in content:
                            unused.append(cid)
                        html_tag = comp.get("html_tag")
                        if cid and isinstance(html_tag, str) and html_tag:
                            tag_map[html_tag] = cid
                if unused:
                    warnings.append(
                        "components defined but not referenced in HTML: "
                        + ", ".join(sorted(unused))
                    )

                # -- 4. Raw tag detection -----------------------------------
                # For each opening <tag> occurrence, check whether it
                # references the component via data-component="id" or a
                # CSS class matching the component id.  Only flag tags that
                # have no such reference — a properly-wired component tag
                # is fine even if the native element is present.
                for tag, comp_id in sorted(tag_map.items()):
                    for m in re.finditer(
                        rf"<{re.escape(tag)}\b([^>]*?)(/?>)", content
                    ):
                        attrs = m.group(1)
                        # data-component="comp_id"
                        has_data = re.search(
                            rf"data-component=[\"']?{re.escape(comp_id)}[\"']?",
                            attrs,
                        )
                        # class="... comp_id ..." (exact token in space-separated list)
                        has_class = False
                        class_m = re.search(r'class=["\']([^"\']*)["\']', attrs)
                        if class_m and comp_id in class_m.group(1).split():
                            has_class = True
                        if not has_data and not has_class:
                            errors.append(
                                f"found raw <{tag}> without component '{comp_id}'"
                                f" — add data-component=\"{comp_id}\" or"
                                f" class=\"{comp_id}\""
                            )
                            break  # one error per component type is enough

    return errors, warnings

