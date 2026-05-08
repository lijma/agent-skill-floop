"""floop CLI entry point."""

import json
import os
from pathlib import Path

import click

from floop import __version__
from floop.adapters import (
    ADAPTERS,
    SUPPORTED_AGENTS,
)


@click.group()
@click.version_option(__version__, prog_name="floop")
def main():
    """floop — AI-native prototype quality toolkit.

    Manage your design like code. Agent Skill + review workflow CLI.

    \b
    Quick start:
      floop init              Initialize a floop project
      floop enable copilot    Install skills (GitHub Copilot)
      floop enable cursor     Install skills (Cursor)
      floop enable claude     Install skills (Claude Code)
      floop enable trae       Install skills (Trae IDE)
      floop enable qwen-code  Install skills (Qwen Code)
      floop enable opencode   Install skills (OpenCode)
      floop enable openclaw   Install skills (OpenClaw)
      floop review            Upload a saved version to floop-server
    """


@main.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def init(project_dir: Path):
    """Initialize a floop project.

    Creates a .floop/ directory with subdirectories for prototypes,
    design tokens, and project configuration.
    """
    project_dir = project_dir.resolve()
    floop_dir = project_dir / ".floop"

    if floop_dir.exists():
        click.secho("⚠ .floop/ already exists, skipping initialization.", fg="yellow")
        return

    # Create directory structure
    dirs = {
        "build": "Generated artifacts (token previews, component views, prototype pages)",
        "tokens": "Design system tokens (colors, typography, spacing)",
        "versions": "Prototype version snapshots (read-only archives)",
    }

    for name in dirs:
        (floop_dir / name).mkdir(parents=True, exist_ok=True)

    # Write config file
    config = {
        "version": __version__,
    }
    import json
    config_path = floop_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    # Write .gitignore inside .floop
    gitignore_path = floop_dir / ".gitignore"
    gitignore_path.write_text(
        "# Generated artifacts — track via floop-server, not git\n"
        "build/\n"
        "/floop.env\n",
        encoding="utf-8",
    )

    click.secho("✓ floop project initialized", fg="green", bold=True)
    click.echo(f"  .floop/config.json")
    click.echo(f"  .floop/build/")
    click.echo(f"  .floop/tokens/")
    click.echo(f"  .floop/versions/")


@main.command()
@click.argument("agent", type=click.Choice(SUPPORTED_AGENTS, case_sensitive=False))
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def enable(agent: str, project_dir: Path):
    """Install floop skills into an AI agent platform.

    \b
    Supported agents:
      copilot    GitHub Copilot (VS Code) — .github/skills/ + .github/instructions/
      cursor     Cursor — .cursor/rules/
      claude     Claude Code — .claude/skills/ + CLAUDE.md
      trae       Trae IDE — .trae/project_rules.md
      qwen-code  Qwen Code (CLI) — AGENTS.md
      opencode   OpenCode (CLI) — .opencode/skills/ + AGENTS.md
      openclaw   OpenClaw — .openclaw/skills/ + AGENTS.md
    """
    project_dir = project_dir.resolve()
    adapter = ADAPTERS[agent]()
    created = adapter.install(project_dir)

    click.secho(f"✓ floop skills installed for {agent}", fg="green", bold=True)
    for path in created:
        rel = path.relative_to(project_dir)
        click.echo(f"  {rel}")


if __name__ == "__main__":
    main()  # pragma: no cover


# ---------------------------------------------------------------------------
# floop token — Design Token management (W3C DTCG)
# ---------------------------------------------------------------------------


@main.group()
def token():
    """Manage design tokens (W3C DTCG format).

    \b
    Commands:
      floop token init       Generate default token files
      floop token validate   Validate token files
      floop token view       Generate HTML preview page
    """


@token.command("init")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing token files.",
)
def token_init_cmd(project_dir: Path, force: bool):
    """Generate W3C DTCG token template files.

    Creates three files in .floop/tokens/:
      global.tokens.json     Primitive design values
      semantic.tokens.json   Semantic aliases
      component.tokens.json  Component-level tokens
    """
    from floop.tokens import token_init

    project_dir = project_dir.resolve()
    tokens_dir = project_dir / ".floop" / "tokens"

    if not (project_dir / ".floop").exists():
        click.secho(
            "⚠ .floop/ not found. Run 'floop init' first.", fg="yellow", err=True
        )
        raise SystemExit(1)

    existing = list(tokens_dir.glob("*.tokens.json"))
    if existing and not force:
        click.secho(
            "⚠ Token files already exist. Use --force to overwrite.", fg="yellow"
        )
        return

    created = token_init(tokens_dir)

    click.secho("✓ Token files generated (W3C DTCG format)", fg="green", bold=True)
    for path in created:
        rel = path.relative_to(project_dir)
        click.echo(f"  {rel}")


@token.command("validate")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
@click.option(
    "--json-output",
    "output_json",
    is_flag=True,
    default=False,
    help="Output structured JSON (for Agent consumption).",
)
def token_validate_cmd(project_dir: Path, output_json: bool):
    """Validate design token files against W3C DTCG spec.

    \b
    Three validation layers:
      L1  Format compliance (valid JSON, valid $type/$value)
      L2  Reference integrity (broken refs, circular deps)
      L3  Design suggestions (recommended semantic tokens)
    """
    from floop.tokens import token_validate

    project_dir = project_dir.resolve()
    tokens_dir = project_dir / ".floop" / "tokens"

    result = token_validate(tokens_dir)

    if output_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        stats = result["stats"]
        click.echo(
            f"Checked {stats['files']} file(s): "
            f"{stats['tokens']} tokens, "
            f"{stats['references']} references, "
            f"{stats['groups']} groups"
        )

        for err in result["errors"]:
            loc = err["path"] or err["file"]
            click.secho(f"  ✗ [{err['code']}] {loc}: {err['message']}", fg="red")
            if err.get("suggestion"):
                click.echo(f"    → {err['suggestion']}")

        for warn in result["warnings"]:
            loc = warn["path"] or warn["file"]
            click.secho(
                f"  ⚠ [{warn['code']}] {loc}: {warn['message']}", fg="yellow"
            )
            if warn.get("suggestion"):
                click.echo(f"    → {warn['suggestion']}")

        if result["valid"]:
            click.secho("✓ All tokens valid", fg="green", bold=True)
        else:
            click.secho(
                f"✗ {len(result['errors'])} error(s) found",
                fg="red",
                bold=True,
            )
            raise SystemExit(1)


@token.command("view")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def token_view_cmd(project_dir: Path):
    """Generate an HTML preview page for design tokens.

    Reads all .tokens.json files, resolves references, and generates
    a visual preview at .floop/build/design-tokens.html.
    """
    from floop.tokens import token_view

    project_dir = project_dir.resolve()
    tokens_dir = project_dir / ".floop" / "tokens"

    if not tokens_dir.exists():
        click.secho(
            "⚠ .floop/tokens/ not found. Run 'floop init' and 'floop token init' first.",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)

    token_files = list(tokens_dir.glob("*.tokens.json"))
    if not token_files:
        click.secho(
            "⚠ No .tokens.json files found. Run 'floop token init' first.",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)

    build_dir = project_dir / ".floop" / "build" / "tokens"
    build_dir.mkdir(parents=True, exist_ok=True)
    out_path = token_view(tokens_dir, out_dir=build_dir)
    css_path = build_dir / "tokens.css"
    click.secho("✓ Token preview generated", fg="green", bold=True)
    click.echo(f"  {out_path.relative_to(project_dir)}")
    click.echo(f"  {css_path.relative_to(project_dir)}")


# ---------------------------------------------------------------------------
# floop preview — Local preview server
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
@click.option(
    "--port",
    type=int,
    default=0,
    help="Port number (default: auto-assign a free port).",
)
@click.option(
    "--version",
    "active_version",
    default="trunk",
    help="Version to preview (default: trunk = current build).",
)
def preview(project_dir: Path, port: int, active_version: str):
    """Start a local web server to preview floop output.

    Renders a navigation index page at request time and serves it on
    a temporary local port. Open the printed URL in your browser to
    browse design tokens, components, and prototype pages.

    Use --version to start preview pinned to a named snapshot.

    Press Ctrl+C to stop the server.
    """
    import http.server
    import socket

    from floop.preview import create_preview_request_handler

    project_dir = project_dir.resolve()
    floop_dir = project_dir / ".floop"

    if not floop_dir.exists():
        click.secho(
            "⚠ .floop/ not found. Run 'floop init' first.", fg="yellow", err=True
        )
        raise SystemExit(1)

    build_dir = floop_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Serve from .floop/ so both build/ and versions/ are reachable.
    # The preview index is virtual and is not written into .floop/build/.
    handler = create_preview_request_handler(
        floop_dir,
        build_dir,
        active_version=active_version,
    )

    # Find a free port if port=0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))
        chosen_port = s.getsockname()[1]

    server = http.server.HTTPServer(("127.0.0.1", chosen_port), handler)

    click.secho("floop preview server", fg="green", bold=True)
    click.echo(f"  http://127.0.0.1:{chosen_port}/")
    click.echo("\n  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        click.echo("\nServer stopped.")


# ---------------------------------------------------------------------------
# floop prd — Product Requirements Document management
# ---------------------------------------------------------------------------


@main.group()
def prd():
    """Manage product requirements document (.floop/prd.md).

    \b
    Commands:
      floop prd init       Create prd.md template
      floop prd validate   Validate prd.md frontmatter
    """


@prd.command("init")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def prd_init_cmd(project_dir: Path):
    """Create .floop/prd.md from template.

    Generates a PRD document with YAML frontmatter (product, target_users,
    core_flows, css_framework, status) and Markdown sections for you to fill in.
    """
    from floop.prototype import prd_init

    project_dir = project_dir.resolve()
    try:
        path = prd_init(project_dir)
    except FileExistsError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    rel = path.relative_to(project_dir)
    click.secho("✓ prd.md created", fg="green", bold=True)
    click.echo(f"  {rel}")


@prd.command("validate")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def prd_validate_cmd(project_dir: Path):
    """Validate .floop/prd.md frontmatter fields."""
    from floop.prototype import prd_validate

    project_dir = project_dir.resolve()
    errors, warnings = prd_validate(project_dir)

    for warn in warnings:
        click.secho(f"  ⚠ {warn}", fg="yellow")
    for err in errors:
        click.secho(f"  ✗ {err}", fg="red")

    if errors:
        click.secho(f"✗ {len(errors)} error(s) found", fg="red", bold=True)
        raise SystemExit(1)

    click.secho("✓ prd.md is valid", fg="green", bold=True)


# ---------------------------------------------------------------------------
# floop sitemap — Sitemap management
# ---------------------------------------------------------------------------


@main.group()
def sitemap():
    """Manage sitemap definition (.floop/sitemap.md).

    \b
    Commands:
      floop sitemap init       Create sitemap.md template
      floop sitemap validate   Validate sitemap.md frontmatter
    """


@sitemap.command("init")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def sitemap_init_cmd(project_dir: Path):
    """Create .floop/sitemap.md from template.

    Generates a sitemap document with YAML frontmatter listing pages
    (id, title, file, status) for you to fill in.
    """
    from floop.prototype import sitemap_init

    project_dir = project_dir.resolve()
    try:
        path = sitemap_init(project_dir)
    except FileExistsError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    rel = path.relative_to(project_dir)
    click.secho("✓ sitemap.md created", fg="green", bold=True)
    click.echo(f"  {rel}")


@sitemap.command("validate")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def sitemap_validate_cmd(project_dir: Path):
    """Validate .floop/sitemap.md frontmatter fields."""
    from floop.prototype import sitemap_validate

    project_dir = project_dir.resolve()
    errors, warnings = sitemap_validate(project_dir)

    for warn in warnings:
        click.secho(f"  ⚠ {warn}", fg="yellow")
    for err in errors:
        click.secho(f"  ✗ {err}", fg="red")

    if errors:
        click.secho(f"✗ {len(errors)} error(s) found", fg="red", bold=True)
        raise SystemExit(1)

    click.secho("✓ sitemap.md is valid", fg="green", bold=True)


# ---------------------------------------------------------------------------
# floop component — Component library management
# ---------------------------------------------------------------------------


@main.group()
def component():
    """Manage component library definition (.floop/components.yaml).

    \b
    Commands:
      floop component init       Create components.yaml template
      floop component validate   Validate components.yaml
    """


@component.command("init")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def component_init_cmd(project_dir: Path):
    """Create .floop/components.yaml from template.

    Generates a component library file with YAML structure
    (id, title, status, tokens) for you to fill in.
    """
    from floop.prototype import component_init

    project_dir = project_dir.resolve()
    try:
        path = component_init(project_dir)
    except FileExistsError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    rel = path.relative_to(project_dir)
    click.secho("✓ components.yaml created", fg="green", bold=True)
    click.echo(f"  {rel}")


@component.command("validate")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def component_validate_cmd(project_dir: Path):
    """Validate .floop/components.yaml fields."""
    from floop.prototype import component_validate

    project_dir = project_dir.resolve()
    errors, warnings = component_validate(project_dir)

    for warn in warnings:
        click.secho(f"  ⚠ {warn}", fg="yellow")
    for err in errors:
        click.secho(f"  ✗ {err}", fg="red")

    if errors:
        click.secho(f"✗ {len(errors)} error(s) found", fg="red", bold=True)
        raise SystemExit(1)

    click.secho("✓ components.yaml is valid", fg="green", bold=True)


# ---------------------------------------------------------------------------
# floop prototype — Journey Map management
# ---------------------------------------------------------------------------


@main.group()
def prototype():
    """Manage prototype journey map (.floop/journey-map.csv).

    \b
    Commands:
      floop prototype init       Build journey-map.csv from sitemap.md
      floop prototype validate   Validate journey HTMLs against journey-map.csv
    """


@prototype.command("init")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def prototype_init_cmd(project_dir: Path):
    """Build .floop/journey-map.csv from sitemap.md.

    Reads all pages in sitemap.md frontmatter and generates a CSV mapping
    sitemap domains to HTML files.  The domain is taken from each page's
    optional 'domain' field; if absent it is derived from the file path
    (e.g. build/journey/auth/login.html → domain 'auth').

    The CSV is always regenerated — safe to re-run after updating sitemap.md.
    """
    from floop.prototype import prototype_init

    project_dir = project_dir.resolve()
    try:
        path = prototype_init(project_dir)
    except FileNotFoundError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    rel = path.relative_to(project_dir)
    click.secho("✓ journey-map.csv generated", fg="green", bold=True)
    click.echo(f"  {rel}")


@prototype.command("validate")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def prototype_validate_cmd(project_dir: Path):
    """Validate journey HTML files against journey-map.csv and sitemap.md.

    \b
    Two checks:
      1. Every HTML under .floop/build/journey/ is mapped in journey-map.csv
      2. Every domain in journey-map.csv exists in sitemap.md pages
    """
    from floop.prototype import prototype_validate

    project_dir = project_dir.resolve()
    errors, warnings = prototype_validate(project_dir)

    for warn in warnings:
        click.secho(f"  ⚠ {warn}", fg="yellow")
    for err in errors:
        click.secho(f"  ✗ {err}", fg="red")

    if errors:
        click.secho(f"✗ {len(errors)} error(s) found", fg="red", bold=True)
        raise SystemExit(1)

    click.secho("✓ prototype is valid", fg="green", bold=True)


# ---------------------------------------------------------------------------
# floop version — Trunk-based prototype version snapshots
# ---------------------------------------------------------------------------


@main.group()
def version():
    """Manage prototype versions (trunk-based snapshots).

    \b
    Commands:
      floop version create   Snapshot current build into a named version
      floop version list     List all versions
    """


@version.command("create")
@click.argument("name")
@click.option("-m", "--message", default="", help="Version description.")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def version_create_cmd(name: str, message: str, project_dir: Path):
    """Snapshot .floop/build/ into .floop/versions/NAME/.

    NAME must be unique (e.g. v1.0, v1.1-homepage-revamp).
    Always run this before sharing a build with a client.
    """
    from floop.prototype import version_create

    project_dir = project_dir.resolve()
    if not (project_dir / ".floop").exists():
        click.secho(
            "⚠ .floop/ not found. Run 'floop init' first.", fg="yellow", err=True
        )
        raise SystemExit(1)

    try:
        version_dir = version_create(project_dir, name, message)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    rel = version_dir.relative_to(project_dir)
    click.secho(f"✓ Version '{name}' created", fg="green", bold=True)
    click.echo(f"  {rel}")


@version.command("list")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def version_list_cmd(project_dir: Path):
    """List all prototype versions."""
    from floop.prototype import version_list

    project_dir = project_dir.resolve()
    versions = version_list(project_dir)

    if not versions:
        click.echo("No versions found. Run 'floop version create' to create one.")
        return

    for v in versions:
        date = v.get("created_at", "")[:10]
        msg = v.get("message", "")
        suffix = f"  {msg}" if msg else ""
        click.echo(f"  {v['version']}  ({date}){suffix}")


# ---------------------------------------------------------------------------
# floop review — Upload saved versions to floop-server
# ---------------------------------------------------------------------------


@main.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
@click.option(
    "--server-url",
    default=None,
    help="floop-server base URL (default: configured value or public SaaS).",
)
@click.option(
    "--project-key",
    default=None,
    help="floop-server project key (default: .floop/floop.env or configured value).",
)
@click.option(
    "--api-key",
    default=None,
    help="floop API key (default: .floop/floop.env, then FLOOP_API_KEY).",
)
@click.option(
    "--version",
    "upload_version",
    default=None,
    help="Version snapshot to upload (default: latest saved version; use trunk explicitly for current build).",
)
@click.option(
    "--json-output",
    "output_json",
    is_flag=True,
    default=False,
    help="Output structured JSON for Agent consumption.",
)
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="HTTP upload timeout in seconds.",
)
def review(
    ctx: click.Context,
    project_dir: Path,
    server_url: str | None,
    project_key: str | None,
    api_key: str | None,
    upload_version: str | None,
    output_json: bool,
    timeout: int,
):
    """Upload a saved prototype version to floop-server for review.

    The command reads .floop/floop.env and uploads review artifacts. If required
    settings are missing, it creates a template and asks you to run
    'floop review set' before uploading.
    """
    if ctx.invoked_subcommand is not None:
        return

    from floop.review import (
        DEFAULT_SERVER_URL,
        ReviewError,
        create_review_archive,
        get_review_env,
        normalize_server_url,
        resolve_review_source,
        save_review_env,
        upload_review,
        write_review_env_template,
    )

    project_dir = project_dir.resolve()
    try:
        if not (project_dir / ".floop").exists():
            raise ReviewError(".floop/ not found. Run 'floop init' first.")

        env_server, env_project, env_api_key = get_review_env(project_dir)
        resolved_server = server_url or env_server or DEFAULT_SERVER_URL
        resolved_project = project_key or env_project

        resolved_server = normalize_server_url(resolved_server)
        api_key = api_key or env_api_key or os.environ.get("FLOOP_API_KEY")

        if not resolved_project or not api_key:
            env_path = write_review_env_template(
                project_dir,
                server_url=resolved_server,
                project_key=resolved_project,
                api_key=api_key,
            )
            rel_env_path = env_path.relative_to(project_dir)
            missing = []
            if not api_key:
                missing.append("FLOOP_API_KEY")
            if not resolved_project:
                missing.append("FLOOP_PROJECT_KEY")
            setup_payload = {
                "status": "setup_required",
                "uploaded": False,
                "serverUrl": resolved_server,
                "envPath": str(rel_env_path),
                "missing": missing,
                "nextCommand": "floop review set",
                "message": "Review setup is required before upload.",
            }
            if output_json:
                click.echo(json.dumps(setup_payload, indent=2, ensure_ascii=False))
                return
            click.secho("⚠ floop review setup required", fg="yellow")
            click.echo(f"Created or updated {rel_env_path} with review settings template.")
            click.echo(f"Missing: {', '.join(missing)}.")
            click.echo("NEXT: run 'floop review set' now.")
            click.echo(
                "This is setup, not a build/upload failure; do not inspect source or retry 'floop review' before setup passes."
            )
            return

        resolved_project = resolved_project.strip()

        save_review_env(project_dir, resolved_server, resolved_project, api_key)
        source_dir, version_label = resolve_review_source(project_dir, upload_version)
        archive_bytes = create_review_archive(source_dir)
        result = upload_review(
            server_url=resolved_server,
            project_key=resolved_project,
            api_key=api_key,
            archive_bytes=archive_bytes,
            version_label=version_label,
            timeout=timeout,
        )
    except ReviewError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    payload = {
        "serverUrl": resolved_server,
        "projectKey": result.get("projectKey") or result.get("projectId") or resolved_project,
        "versionId": result.get("versionId"),
        "versionLabel": version_label,
        "previewUrl": result.get("previewUrl"),
        "shareUrl": result.get("shareUrl"),
        "status": result.get("status"),
    }

    if output_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.secho("✓ Review version uploaded", fg="green", bold=True)
    click.echo(f"  version: {version_label}")
    click.echo(f"  preview: {payload['previewUrl']}")
    click.echo(f"  share: {payload['shareUrl']}")


@review.command("set")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
@click.option(
    "--server-url",
    default=None,
    help="floop-server base URL (default: existing value or public SaaS).",
)
@click.option(
    "--api-key",
    default=None,
    help="floop API key (default: existing value, FLOOP_API_KEY, or secure prompt).",
)
@click.option(
    "--project-key",
    default=None,
    help="Use an existing floop-server project key.",
)
@click.option(
    "--project-name",
    default=None,
    help="Project name to create when no project exists.",
)
@click.option(
    "--project-slug",
    default=None,
    help="Optional slug when creating a project.",
)
@click.option(
    "--json-output",
    "output_json",
    is_flag=True,
    default=False,
    help="Output structured JSON for Agent consumption.",
)
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="HTTP timeout in seconds.",
)
def review_set(
    project_dir: Path,
    server_url: str | None,
    api_key: str | None,
    project_key: str | None,
    project_name: str | None,
    project_slug: str | None,
    output_json: bool,
    timeout: int,
):
    """Configure .floop/floop.env and verify floop-server access."""
    from floop.review import (
        DEFAULT_SERVER_URL,
        ReviewError,
        create_review_project,
        get_review_env,
        list_review_projects,
        normalize_server_url,
        save_review_env,
        write_review_env_template,
    )

    project_dir = project_dir.resolve()
    try:
        if not (project_dir / ".floop").exists():
            raise ReviewError(".floop/ not found. Run 'floop init' first.")

        env_server, env_project, env_api_key = get_review_env(project_dir)
        resolved_server = normalize_server_url(server_url or env_server or DEFAULT_SERVER_URL)
        resolved_api_key = api_key or env_api_key or os.environ.get("FLOOP_API_KEY")

        if not resolved_api_key:
            write_review_env_template(project_dir, server_url=resolved_server)
            resolved_api_key = click.prompt("floop API key", hide_input=True)

        projects = list_review_projects(
            server_url=resolved_server,
            api_key=resolved_api_key,
            timeout=timeout,
        )
        active_projects = [p for p in projects if p.get("status") != "suspended"]
        resolved_project = project_key or env_project

        if resolved_project:
            matching = [p for p in projects if p.get("id") == resolved_project]
            if not matching:
                raise ReviewError("Project key not found for this API key.")
            selected_project = matching[0]
        elif len(active_projects) == 1:
            selected_project = active_projects[0]
            resolved_project = str(selected_project["id"])
        elif not active_projects:
            created_name = project_name or project_dir.name or "Floop Project"
            selected_project = create_review_project(
                server_url=resolved_server,
                api_key=resolved_api_key,
                name=created_name,
                slug=project_slug,
                timeout=timeout,
            )
            resolved_project = str(selected_project["id"])
        else:
            click.echo("Multiple floop projects found:")
            for index, project in enumerate(active_projects, start=1):
                name = project.get("name") or "Untitled"
                project_key = project.get("id") or "no-key"
                click.echo(f"  {index}. {name} ({project_key})")
            choice = click.prompt("Choose project", type=click.IntRange(1, len(active_projects)))
            selected_project = active_projects[choice - 1]
            resolved_project = str(selected_project["id"])

        env_path = save_review_env(
            project_dir,
            resolved_server,
            resolved_project,
            resolved_api_key,
        )
    except ReviewError as exc:
        click.secho(f"⚠ {exc}", fg="yellow", err=True)
        raise SystemExit(1)

    payload = {
        "serverUrl": resolved_server,
        "projectKey": resolved_project,
        "projectName": selected_project.get("name"),
        "projectSlug": selected_project.get("slug"),
        "envPath": str(env_path.relative_to(project_dir)),
        "projectCount": len(projects),
    }

    if output_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.secho("✓ floop review settings saved", fg="green", bold=True)
    click.echo(f"  server: {payload['serverUrl']}")
    click.echo(f"  project: {payload['projectName'] or payload['projectKey']}")
    click.echo(f"  env: {payload['envPath']}")
    click.echo("  next: floop review --json-output")


# ---------------------------------------------------------------------------
# floop feedback — Fetch reviewer comments from floop-server
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--version",
    default=None,
    help="Version label to fetch comments for (default: latest version).",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="floop project directory (default: current directory).",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Print structured JSON instead of human-readable text.",
)
def feedback(
    version: str | None,
    project_dir: Path | None,
    json_output: bool,
):
    """Fetch and display reviewer comments from floop-server.

    Retrieves comments for the latest version, or for a specific version if --version is provided.
    Requires .floop/floop.env with FLOOP_SERVER_URL, FLOOP_PROJECT_KEY, and FLOOP_API_KEY.

    \b
    Examples:
      floop feedback
      floop feedback --version v1.0
      floop feedback --json-output
    """
    from floop.review import (
        ReviewError,
        get_review_comments,
        get_review_env,
        list_review_versions,
    )

    project = project_dir or Path.cwd()
    if not (project / ".floop").is_dir():
        raise click.ClickException(
            f".floop/ directory not found in {project}\n"
            "Run 'floop init' to initialize a floop project."
        )

    # Load configuration from .floop/floop.env
    server_url, project_key, api_key = get_review_env(project)
    missing = []
    if not server_url:
        missing.append("FLOOP_SERVER_URL")
    if not project_key:
        missing.append("FLOOP_PROJECT_KEY")
    if not api_key:
        missing.append("FLOOP_API_KEY")

    if missing:
        if json_output:
            error_payload = {
                "error": "SETUP_REQUIRED",
                "message": "Review settings not configured.",
                "missing": missing,
                "nextCommand": "floop review set",
            }
            click.echo(json.dumps(error_payload, indent=2, ensure_ascii=False))
            return

        click.secho("✗ Review settings not configured", fg="red", bold=True)
        click.echo(f"  Missing: {', '.join(missing)}")
        click.echo("")
        click.echo("NEXT: run 'floop review set' to configure server/API key/project, then try again.")
        return

    try:
        # Fetch versions list
        versions = list_review_versions(
            server_url=server_url,
            project_key=project_key,
            api_key=api_key,
        )

        if not versions:
            if json_output:
                click.echo(json.dumps({"comments": [], "message": "No versions found."}, indent=2))
                return

            click.secho("ℹ No versions found for this project.", fg="yellow")
            click.echo("  Publish a version first with 'floop review'.")
            return

        # Find the target version
        if version:
            # User specified a version label
            target_version = None
            for v in versions:
                if v.get("versionLabel") == version:
                    target_version = v
                    break
            if not target_version:
                if json_output:
                    error_payload = {
                        "error": "VERSION_NOT_FOUND",
                        "message": f"Version '{version}' not found.",
                        "availableVersions": [v.get("versionLabel") or v.get("versionId") for v in versions],
                    }
                    click.echo(json.dumps(error_payload, indent=2, ensure_ascii=False))
                    return

                click.secho(f"✗ Version '{version}' not found", fg="red", bold=True)
                click.echo("\nAvailable versions:")
                for v in versions:
                    label = v.get("versionLabel") or v.get("versionId")
                    click.echo(f"  - {label}")
                return
        else:
            # Use the latest version
            target_version = max(versions, key=lambda v: v.get("uploadedAt") or "")

        version_id = target_version.get("versionId")
        version_label = target_version.get("versionLabel") or version_id

        # Fetch comments for this version
        comments = get_review_comments(
            server_url=server_url,
            project_key=project_key,
            version_id=version_id,
            api_key=api_key,
        )

        if json_output:
            output_payload = {
                "versionId": version_id,
                "versionLabel": version_label,
                "commentCount": len(comments),
                "comments": comments,
            }
            click.echo(json.dumps(output_payload, indent=2, ensure_ascii=False))
            return

        # Human-readable output
        if not comments:
            click.secho(f"ℹ No comments yet for version '{version_label}'", fg="yellow")
            click.echo("")
            click.echo("Share the review link with reviewers and check back later.")
            return

        # Count by status
        open_count = sum(1 for c in comments if c.get("status") == "open")
        in_review_count = sum(1 for c in comments if c.get("status") == "in_review")
        resolved_count = sum(1 for c in comments if c.get("status") == "resolved")

        # Count by priority
        critical_count = sum(1 for c in comments if c.get("priority") == "critical")
        high_count = sum(1 for c in comments if c.get("priority") == "high")
        medium_count = sum(1 for c in comments if c.get("priority") == "medium")
        low_count = sum(1 for c in comments if c.get("priority") == "low")

        click.secho(f"📝 Review Feedback for '{version_label}'", fg="cyan", bold=True)
        click.echo("")
        click.echo(f"Total comments: {len(comments)}")
        click.echo(f"  Open: {open_count} | In review: {in_review_count} | Resolved: {resolved_count}")
        click.echo(f"  Priority: Critical: {critical_count} | High: {high_count} | Medium: {medium_count} | Low: {low_count}")
        click.echo("")

        # Show high-priority and critical comments
        priority_comments = [c for c in comments if c.get("priority") in {"critical", "high"}]
        if priority_comments:
            click.secho("High-Priority Comments:", fg="yellow", bold=True)
            for c in priority_comments[:10]:  # Limit to first 10
                author = c.get("authorName") or "Anonymous"
                body = c.get("body") or "(no text)"
                priority = c.get("priority") or "medium"
                labels = c.get("labels") or []
                anchor = c.get("anchor") or {}
                path = anchor.get("path") or "general"

                priority_badge = "🔴" if priority == "critical" else "🟠"
                labels_str = f" [{', '.join(labels)}]" if labels else ""
                click.echo(f"  {priority_badge} {author} on {path}: {body[:80]}{labels_str}")
            click.echo("")

        click.echo("Use '--json-output' to see full comment details.")
        click.echo("Run 'floop review' to publish an updated version after addressing feedback.")

    except ReviewError as exc:
        if json_output:
            error_payload = {"error": "FEEDBACK_FAILED", "message": str(exc)}
            click.echo(json.dumps(error_payload, indent=2, ensure_ascii=False))
            raise SystemExit(1)

        click.secho(f"✗ {exc}", fg="red", bold=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# floop journey — Journey backward-check commands
# ---------------------------------------------------------------------------


@main.group()
def journey():
    """Manage journey HTML pages.

    \b
    Commands:
      floop journey check   Backward-check a journey HTML for token/component gaps
    """


@journey.command("check")
@click.argument(
    "html_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (default: current directory).",
)
def journey_check_cmd(html_file: Path, project_dir: Path):
    """Backward-check a journey HTML file for token and component gaps.

    Scans HTML_FILE for missing token references, unused components,
    and missing head links (tokens.css / components.js).
    """
    from floop.prototype import journey_check

    project_dir = project_dir.resolve()
    html_file = html_file.resolve()

    if not (project_dir / ".floop").exists():
        click.secho(
            "⚠ .floop/ not found. Run 'floop init' first.", fg="yellow", err=True
        )
        raise SystemExit(1)

    errors, warnings = journey_check(project_dir, html_file)

    for warn in warnings:
        click.secho(f"  ⚠ {warn}", fg="yellow")
    for err in errors:
        click.secho(f"  ✗ {err}", fg="red")

    if errors:
        click.secho(
            f"✗ {len(errors)} error(s) found", fg="red", bold=True
        )
        raise SystemExit(1)

    click.secho("✓ journey check passed", fg="green", bold=True)
