"""floop CLI entry point."""

import json
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
        "build/\n",
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

    Generates a navigation index page in .floop/build/ and serves it on
    a temporary local port.  Open the printed URL in your browser to
    browse design tokens, components, and prototype pages.

    Use --version to start preview pinned to a named snapshot.

    Press Ctrl+C to stop the server.
    """
    import http.server
    import functools
    import socket

    from floop.preview import generate_preview_index

    project_dir = project_dir.resolve()
    floop_dir = project_dir / ".floop"

    if not floop_dir.exists():
        click.secho(
            "⚠ .floop/ not found. Run 'floop init' first.", fg="yellow", err=True
        )
        raise SystemExit(1)

    build_dir = floop_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Generate (or refresh) the navigation index page
    generate_preview_index(build_dir, active_version=active_version)

    # Serve from .floop/ so both build/ and versions/ are reachable
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(floop_dir)
    )

    # Find a free port if port=0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))
        chosen_port = s.getsockname()[1]

    server = http.server.HTTPServer(("127.0.0.1", chosen_port), handler)

    click.secho("floop preview server", fg="green", bold=True)
    click.echo(f"  http://127.0.0.1:{chosen_port}/build/")
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
