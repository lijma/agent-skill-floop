"""floop token management — W3C DTCG format support.

Handles initialization and validation of design tokens following
the W3C Design Tokens Format Module (DTCG) specification.

Three-layer architecture:
  global.tokens.json    — primitive values (colors, dimensions, fonts)
  semantic.tokens.json  — semantic aliases referencing global tokens
  component.tokens.json — component-level tokens referencing semantic/global
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# W3C DTCG supported $type values
DTCG_TYPES = frozenset({
    "color",
    "dimension",
    "fontFamily",
    "fontWeight",
    "duration",
    "cubicBezier",
    "number",
    "strokeStyle",
    "border",
    "transition",
    "shadow",
    "gradient",
    "typography",
})

# Recommended semantic tokens — used for L3 suggestions
RECOMMENDED_SEMANTIC_TOKENS = {
    "color": [
        "color.primary",
        "color.background",
        "color.text",
        "color.border",
    ],
    "dimension": [
        "spacing.base",
    ],
    "fontFamily": [
        "font.body",
    ],
}


# ---------------------------------------------------------------------------
# Token templates (W3C DTCG format)
# ---------------------------------------------------------------------------

GLOBAL_TOKENS: dict[str, Any] = {
    "color": {
        "blue-500": {
            "$type": "color",
            "$value": "#2563EB",
            "$description": "Primary blue",
        },
        "purple-500": {
            "$type": "color",
            "$value": "#7C3AED",
            "$description": "Secondary purple",
        },
        "amber-500": {
            "$type": "color",
            "$value": "#F59E0B",
            "$description": "Accent amber",
        },
        "white": {
            "$type": "color",
            "$value": "#FFFFFF",
        },
        "gray-50": {
            "$type": "color",
            "$value": "#F8FAFC",
        },
        "gray-100": {
            "$type": "color",
            "$value": "#F1F5F9",
        },
        "gray-200": {
            "$type": "color",
            "$value": "#E2E8F0",
        },
        "gray-500": {
            "$type": "color",
            "$value": "#64748B",
        },
        "gray-900": {
            "$type": "color",
            "$value": "#0F172A",
        },
        "red-500": {
            "$type": "color",
            "$value": "#EF4444",
            "$description": "Error / danger",
        },
        "green-500": {
            "$type": "color",
            "$value": "#22C55E",
            "$description": "Success",
        },
    },
    "dimension": {
        "space-1": {"$type": "dimension", "$value": "4px"},
        "space-2": {"$type": "dimension", "$value": "8px"},
        "space-3": {"$type": "dimension", "$value": "12px"},
        "space-4": {"$type": "dimension", "$value": "16px"},
        "space-6": {"$type": "dimension", "$value": "24px"},
        "space-8": {"$type": "dimension", "$value": "32px"},
        "space-12": {"$type": "dimension", "$value": "48px"},
        "space-16": {"$type": "dimension", "$value": "64px"},
        "radius-sm": {"$type": "dimension", "$value": "4px"},
        "radius-md": {"$type": "dimension", "$value": "8px"},
        "radius-lg": {"$type": "dimension", "$value": "12px"},
        "radius-full": {"$type": "dimension", "$value": "9999px"},
    },
    "fontFamily": {
        "sans": {
            "$type": "fontFamily",
            "$value": "Inter, system-ui, sans-serif",
        },
        "mono": {
            "$type": "fontFamily",
            "$value": "JetBrains Mono, monospace",
        },
    },
    "fontWeight": {
        "regular": {"$type": "fontWeight", "$value": 400},
        "medium": {"$type": "fontWeight", "$value": 500},
        "semibold": {"$type": "fontWeight", "$value": 600},
        "bold": {"$type": "fontWeight", "$value": 700},
    },
}

SEMANTIC_TOKENS: dict[str, Any] = {
    "color": {
        "$description": "Semantic color aliases",
        "primary": {
            "$type": "color",
            "$value": "{color.blue-500}",
        },
        "secondary": {
            "$type": "color",
            "$value": "{color.purple-500}",
        },
        "accent": {
            "$type": "color",
            "$value": "{color.amber-500}",
        },
        "background": {
            "$type": "color",
            "$value": "{color.white}",
        },
        "surface": {
            "$type": "color",
            "$value": "{color.gray-50}",
        },
        "text": {
            "$type": "color",
            "$value": "{color.gray-900}",
        },
        "text-muted": {
            "$type": "color",
            "$value": "{color.gray-500}",
        },
        "border": {
            "$type": "color",
            "$value": "{color.gray-200}",
        },
        "error": {
            "$type": "color",
            "$value": "{color.red-500}",
        },
        "success": {
            "$type": "color",
            "$value": "{color.green-500}",
        },
    },
    "spacing": {
        "$description": "Semantic spacing aliases",
        "base": {
            "$type": "dimension",
            "$value": "{dimension.space-4}",
        },
        "xs": {
            "$type": "dimension",
            "$value": "{dimension.space-1}",
        },
        "sm": {
            "$type": "dimension",
            "$value": "{dimension.space-2}",
        },
        "md": {
            "$type": "dimension",
            "$value": "{dimension.space-4}",
        },
        "lg": {
            "$type": "dimension",
            "$value": "{dimension.space-6}",
        },
        "xl": {
            "$type": "dimension",
            "$value": "{dimension.space-8}",
        },
    },
    "font": {
        "$description": "Semantic font aliases",
        "body": {
            "$type": "fontFamily",
            "$value": "{fontFamily.sans}",
        },
        "code": {
            "$type": "fontFamily",
            "$value": "{fontFamily.mono}",
        },
    },
    "radius": {
        "$description": "Semantic border radius",
        "default": {
            "$type": "dimension",
            "$value": "{dimension.radius-md}",
        },
        "small": {
            "$type": "dimension",
            "$value": "{dimension.radius-sm}",
        },
        "large": {
            "$type": "dimension",
            "$value": "{dimension.radius-lg}",
        },
        "full": {
            "$type": "dimension",
            "$value": "{dimension.radius-full}",
        },
    },
}

COMPONENT_TOKENS: dict[str, Any] = {
    "button": {
        "$description": "Button component tokens",
        "background": {
            "$type": "color",
            "$value": "{color.primary}",
        },
        "text": {
            "$type": "color",
            "$value": "{color.white}",
        },
        "radius": {
            "$type": "dimension",
            "$value": "{radius.default}",
        },
        "padding-x": {
            "$type": "dimension",
            "$value": "{spacing.md}",
        },
        "padding-y": {
            "$type": "dimension",
            "$value": "{spacing.sm}",
        },
    },
    "card": {
        "$description": "Card component tokens",
        "background": {
            "$type": "color",
            "$value": "{color.surface}",
        },
        "border": {
            "$type": "color",
            "$value": "{color.border}",
        },
        "radius": {
            "$type": "dimension",
            "$value": "{radius.large}",
        },
        "padding": {
            "$type": "dimension",
            "$value": "{spacing.lg}",
        },
    },
    "input": {
        "$description": "Input field component tokens",
        "background": {
            "$type": "color",
            "$value": "{color.background}",
        },
        "border": {
            "$type": "color",
            "$value": "{color.border}",
        },
        "text": {
            "$type": "color",
            "$value": "{color.text}",
        },
        "radius": {
            "$type": "dimension",
            "$value": "{radius.default}",
        },
        "padding-x": {
            "$type": "dimension",
            "$value": "{spacing.sm}",
        },
        "padding-y": {
            "$type": "dimension",
            "$value": "{spacing.xs}",
        },
    },
}


# ---------------------------------------------------------------------------
# Token init
# ---------------------------------------------------------------------------

def token_init(tokens_dir: Path) -> list[Path]:
    """Generate three W3C DTCG token files in *tokens_dir*.

    Returns the list of created file paths.
    """
    tokens_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("global.tokens.json", GLOBAL_TOKENS),
        ("semantic.tokens.json", SEMANTIC_TOKENS),
        ("component.tokens.json", COMPONENT_TOKENS),
    ]

    created: list[Path] = []
    for name, data in files:
        path = tokens_dir / name
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created.append(path)

    return created


# ---------------------------------------------------------------------------
# Token validation (L1 format, L2 references, L3 suggestions)
# ---------------------------------------------------------------------------

def _is_token_node(node: dict) -> bool:
    """Check if a dict is a token (has $value) vs a group."""
    return "$value" in node


def _is_group_node(node: dict) -> bool:
    """Check if a dict is a group (has nested dicts, no $value)."""
    if "$value" in node:
        return False
    return any(isinstance(v, dict) for v in node.values())


def _collect_tokens(
    data: dict,
    prefix: str = "",
) -> list[tuple[str, dict]]:
    """Walk the token tree and yield (dotted_path, token_node) pairs."""
    results: list[tuple[str, dict]] = []
    for key, value in data.items():
        if key.startswith("$"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            if _is_token_node(value):
                results.append((path, value))
            else:
                results.extend(_collect_tokens(value, path))
    return results


def _extract_references(value: Any) -> list[str]:
    """Extract {reference.path} strings from a token $value."""
    if isinstance(value, str):
        import re
        return re.findall(r"\{([^}]+)\}", value)
    return []


def _collect_all_paths(data: dict, prefix: str = "") -> set[str]:
    """Collect all token and group paths in a token file."""
    paths: set[str] = set()
    for key, value in data.items():
        if key.startswith("$"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.add(path)
            if _is_token_node(value):
                pass  # leaf token
            else:
                paths.update(_collect_all_paths(value, path))
    return paths


def _detect_circular_refs(
    all_tokens: dict[str, dict],
) -> list[str]:
    """Detect circular references among tokens. Returns list of cycle descriptions."""
    # Build adjacency: token_path -> set of referenced paths
    graph: dict[str, set[str]] = {}
    for path, node in all_tokens.items():
        refs = _extract_references(node.get("$value", ""))
        graph[path] = set(refs)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {p: WHITE for p in graph}
    cycles: list[str] = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, set()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle_start = stack.index(neighbor)
                cycle = stack[cycle_start:] + [neighbor]
                cycles.append(" → ".join(cycle))
            elif color[neighbor] == WHITE:
                dfs(neighbor, stack)
        stack.pop()
        color[node] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node, [])

    return cycles


def token_validate(
    tokens_dir: Path,
) -> dict[str, Any]:
    """Validate token files in *tokens_dir*.

    Returns a structured result dict:
    {
        "valid": bool,
        "errors": [{"code": str, "file": str, "path": str, "message": str, "suggestion": str}],
        "warnings": [{"code": str, "file": str, "path": str, "message": str, "suggestion": str}],
        "stats": {"files": int, "tokens": int, "references": int, "groups": int},
    }
    """
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    total_tokens = 0
    total_refs = 0
    total_groups = 0
    files_checked = 0

    token_files = sorted(tokens_dir.glob("*.tokens.json"))
    if not token_files:
        errors.append({
            "code": "NO_TOKEN_FILES",
            "file": str(tokens_dir),
            "path": "",
            "message": "No .tokens.json files found",
            "suggestion": "Run 'floop token init' to generate default token files.",
        })
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "stats": {"files": 0, "tokens": 0, "references": 0, "groups": 0},
        }

    # Collect all tokens across all files for cross-file reference checking
    all_tokens: dict[str, dict] = {}
    all_paths: set[str] = set()

    for tf in token_files:
        files_checked += 1
        filename = tf.name

        # L1: Parse JSON
        try:
            raw = tf.read_text(encoding="utf-8")
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append({
                "code": "INVALID_JSON",
                "file": filename,
                "path": "",
                "message": f"Invalid JSON: {exc}",
                "suggestion": "Fix JSON syntax errors.",
            })
            continue

        if not isinstance(data, dict):
            errors.append({
                "code": "NOT_OBJECT",
                "file": filename,
                "path": "",
                "message": "Root must be a JSON object",
                "suggestion": "Wrap tokens in a JSON object {}.",
            })
            continue

        # Collect tokens and paths
        tokens = _collect_tokens(data)
        paths = _collect_all_paths(data)
        all_paths.update(paths)

        for path, node in tokens:
            total_tokens += 1
            all_tokens[path] = node

            # L1: Check $type is valid
            token_type = node.get("$type")
            if token_type is not None and token_type not in DTCG_TYPES:
                errors.append({
                    "code": "INVALID_TYPE",
                    "file": filename,
                    "path": path,
                    "message": f"Unknown $type: '{token_type}'",
                    "suggestion": f"Use one of: {', '.join(sorted(DTCG_TYPES))}",
                })

            # L1: Check $value exists (defensive — _collect_tokens guarantees $value)
            value = node.get("$value")

            # Count references
            refs = _extract_references(value)
            total_refs += len(refs)

        # Count groups (non-token dict nodes)
        for key, value in data.items():
            if key.startswith("$"):
                continue
            if isinstance(value, dict) and not _is_token_node(value):
                total_groups += 1

    # L2: Check all references resolve
    for path, node in all_tokens.items():
        refs = _extract_references(node.get("$value", ""))
        for ref in refs:
            if ref not in all_paths:
                errors.append({
                    "code": "BROKEN_REFERENCE",
                    "file": "",
                    "path": path,
                    "message": f"Reference '{{{ref}}}' not found",
                    "suggestion": f"Define '{ref}' in a token file, or fix the reference path.",
                })

    # L2: Circular reference detection
    cycles = _detect_circular_refs(all_tokens)
    for cycle in cycles:
        errors.append({
            "code": "CIRCULAR_REFERENCE",
            "file": "",
            "path": "",
            "message": f"Circular reference: {cycle}",
            "suggestion": "Break the circular dependency between tokens.",
        })

    # L3: Suggest recommended semantic tokens
    for category, recommended in RECOMMENDED_SEMANTIC_TOKENS.items():
        for rec_path in recommended:
            if rec_path not in all_paths:
                warnings.append({
                    "code": "MISSING_RECOMMENDED",
                    "file": "",
                    "path": rec_path,
                    "message": f"Recommended semantic token '{rec_path}' not defined",
                    "suggestion": f"Consider adding '{rec_path}' for better design consistency.",
                })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "files": files_checked,
            "tokens": total_tokens,
            "references": total_refs,
            "groups": total_groups,
        },
    }


# ---------------------------------------------------------------------------
# Token reference resolution
# ---------------------------------------------------------------------------

def _resolve_value(
    value: Any,
    all_tokens: dict[str, dict],
    visited: set[str] | None = None,
) -> Any:
    """Resolve {reference} strings in a token value to concrete values."""
    if not isinstance(value, str):
        return value
    import re

    refs = re.findall(r"\{([^}]+)\}", value)
    if not refs:
        return value

    if visited is None:
        visited = set()

    result = value
    for ref in refs:
        if ref in visited:
            continue  # skip circular
        if ref in all_tokens:
            visited.add(ref)
            resolved = _resolve_value(
                all_tokens[ref].get("$value", ""), all_tokens, visited
            )
            result = result.replace(f"{{{ref}}}", str(resolved))
    return result


def _load_and_resolve_tokens(
    tokens_dir: Path,
) -> tuple[dict[str, dict], dict[str, Any]]:
    """Load all token files and resolve references.

    Returns (all_tokens_dict, resolved_values_dict) where
    resolved_values maps dotted path → concrete value string.
    """
    token_files = sorted(tokens_dir.glob("*.tokens.json"))
    all_tokens: dict[str, dict] = {}

    for tf in token_files:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        for path, node in _collect_tokens(data):
            all_tokens[path] = node

    resolved: dict[str, Any] = {}
    for path, node in all_tokens.items():
        resolved[path] = _resolve_value(node.get("$value", ""), all_tokens)

    return all_tokens, resolved


# ---------------------------------------------------------------------------
# Token view — HTML preview generation
# ---------------------------------------------------------------------------

# Layer display order and metadata
_LAYER_ORDER = ["global", "semantic", "component"]
_TYPE_ORDER = ["color", "dimension", "fontFamily", "fontWeight", "other"]
_TYPE_LABELS: dict[str, str] = {
    "color": "Colors",
    "dimension": "Dimensions",
    "fontFamily": "Font Family",
    "fontWeight": "Font Weight",
    "other": "Other Tokens",
}
_LAYER_META: dict[str, dict[str, str]] = {
    "global": {
        "title": "Global Tokens",
        "subtitle": "Primitive design values — the raw palette. These are concrete values that never reference other tokens.",
        "badge_class": "badge-global",
    },
    "semantic": {
        "title": "Semantic Tokens",
        "subtitle": "Purpose-driven aliases that reference global tokens. Use these in your designs to keep intent clear.",
        "badge_class": "badge-semantic",
    },
    "component": {
        "title": "Component Tokens",
        "subtitle": "Component-specific tokens referencing semantic or global values. Each component gets its own set.",
        "badge_class": "badge-component",
    },
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Design Tokens Preview</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;color:#1a1a2e;background:#f5f6f8;padding:0}
.page-header{background:#fff;border-bottom:1px solid #e2e5ea;padding:2rem 2.5rem 1.5rem}
.page-header h1{font-size:1.6rem;font-weight:700;letter-spacing:-.02em}
.page-header .subtitle{color:#6c757d;font-size:.85rem;margin-top:.35rem}
.nav{display:flex;gap:.5rem;margin-top:1.25rem;flex-wrap:wrap}
.nav a{display:inline-block;padding:.35rem .85rem;border-radius:6px;font-size:.8rem;font-weight:500;text-decoration:none;color:#495057;background:#f0f1f3;transition:background .15s}
.nav a:hover{background:#e2e5ea}
.nav a.active{background:#1a1a2e;color:#fff}
.content{max-width:1200px;margin:0 auto;padding:1.5rem 2.5rem 3rem}
.layer{margin-bottom:2.5rem}
.layer-header{display:flex;align-items:baseline;gap:.75rem;margin-bottom:.25rem}
.layer-header h2{font-size:1.15rem;font-weight:700}
.badge{display:inline-block;padding:.15rem .55rem;border-radius:4px;font-size:.65rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.badge-global{background:#e8f4fd;color:#0369a1}
.badge-semantic{background:#ecfdf5;color:#047857}
.badge-component{background:#fef3c7;color:#92400e}
.badge-other{background:#f3e8ff;color:#6b21a8}
.layer-desc{color:#6c757d;font-size:.82rem;margin-bottom:1.25rem}
.group{margin-bottom:1.5rem}
.group-title{font-size:.85rem;font-weight:600;color:#495057;margin-bottom:.5rem;display:flex;align-items:center;gap:.5rem}
.group-title .gdesc{font-weight:400;color:#868e96;font-size:.78rem}
.subgroup{margin-top:.85rem}
.subgroup-label{font-size:.72rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.45rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:.75rem}
.swatch{border-radius:8px;overflow:hidden;background:#fff;border:1px solid #e9ecef;transition:box-shadow .15s}
.swatch:hover{box-shadow:0 2px 8px rgba(0,0,0,.08)}
.swatch-color{height:64px}
.swatch-info{padding:.6rem .7rem;font-size:.75rem}
.swatch-info .name{font-weight:600;word-break:break-all;line-height:1.3}
.swatch-info .path,.dim-item .path,.font-sample .path,.weight-sample .path,.other-item .path,.spec-cell .path{color:#94a3b8;font-size:.64rem;margin-top:.15rem;word-break:break-all}
.swatch-info .value{color:#6c757d;font-family:monospace;font-size:.7rem;margin-top:.2rem}
.swatch-info .ref{color:#0369a1;font-size:.65rem;margin-top:.15rem}
.swatch-info .chain,.dim-item .chain,.font-sample .chain,.other-item .chain,.spec-cell .chain{color:#7c3aed;font-size:.64rem;margin-top:.15rem;line-height:1.35}
.chain .resolved{color:#6c757d}
.swatch-info .desc{color:#868e96;font-size:.65rem;margin-top:.15rem;font-style:italic}
.color-stack{display:flex;flex-direction:column;gap:.75rem}
.color-pair-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.75rem}
.color-pair{background:#fff;border:1px solid #e9ecef;border-radius:10px;padding:.75rem .85rem}
.color-pair-title{font-size:.74rem;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.45rem}
.color-pair-row{display:grid;grid-template-columns:1fr auto;gap:.4rem .6rem;align-items:center;padding:.35rem 0;border-top:1px solid #f1f3f5}
.color-pair-row:first-of-type{border-top:none;padding-top:0}
.color-pair-row .meta{min-width:0}
.color-pair-row .name{font-weight:600;font-size:.74rem;word-break:break-all}
.color-pair-row .value{font-size:.7rem;color:#6c757d;font-family:monospace}
.color-chip{display:inline-flex;align-items:center;gap:.45rem;padding:.3rem .5rem;border:1px solid #e9ecef;border-radius:999px;background:#fff}
.color-chip .dot{width:12px;height:12px;border-radius:999px;border:1px solid rgba(15,23,42,.12)}
.dim-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.6rem}
.dim-item{background:#fff;border:1px solid #e9ecef;border-radius:8px;padding:.6rem .75rem;font-size:.78rem;display:flex;flex-direction:column;gap:.2rem}
.dim-item .name{font-weight:600}
.dim-item .value{color:#6c757d;font-family:monospace;font-size:.72rem}
.dim-item .ref{color:#0369a1;font-size:.65rem}
.dim-item .bar{height:5px;background:#4c6ef5;border-radius:3px;margin-top:.3rem;max-width:100%}
.font-sample{background:#fff;border:1px solid #e9ecef;border-radius:8px;padding:.85rem 1rem;margin-bottom:.6rem}
.font-sample .name{font-weight:600;font-size:.8rem}
.font-sample .value{color:#6c757d;font-family:monospace;font-size:.72rem}
.font-sample .ref{color:#0369a1;font-size:.65rem}
.font-sample .preview{margin-top:.4rem;font-size:1.2rem}
.weight-grid{display:flex;flex-wrap:wrap;gap:.5rem}
.weight-sample{background:#fff;border:1px solid #e9ecef;border-radius:8px;padding:.6rem .9rem;text-align:center;min-width:80px}
.weight-sample .name{font-weight:600;font-size:.72rem}
.weight-sample .value{color:#6c757d;font-family:monospace;font-size:.68rem}
.weight-sample .preview{margin-top:.2rem;font-size:1.1rem}
.other-item{background:#fff;border:1px solid #e9ecef;border-radius:8px;padding:.6rem .75rem;font-size:.78rem}
.other-item .name{font-weight:600}
.other-item .value{color:#6c757d;font-family:monospace;font-size:.72rem}
.spec-table{background:#fff;border:1px solid #e9ecef;border-radius:10px;overflow:hidden}
.spec-head,.spec-row{display:grid;grid-template-columns:minmax(120px,1fr) minmax(190px,1.6fr) minmax(80px,.7fr) minmax(200px,1.5fr) minmax(130px,1fr);gap:.75rem;padding:.75rem .9rem;align-items:start}
.spec-head{background:#f8fafc;color:#64748b;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.spec-row{border-top:1px solid #eef2f7;font-size:.76rem}
.spec-cell .name{font-weight:600;color:#111827;word-break:break-all}
.spec-cell .token-id{font-family:monospace;color:#475569;font-size:.7rem;word-break:break-all}
.spec-cell .type-pill,.value-pill{display:inline-flex;align-items:center;gap:.4rem;padding:.28rem .5rem;border:1px solid #e2e8f0;border-radius:999px;background:#fff;color:#475569;font-size:.68rem}
.value-pill .swatch{width:12px;height:12px;border-radius:999px;border:1px solid rgba(15,23,42,.12);overflow:hidden}
@media (max-width:900px){.spec-head{display:none}.spec-row{grid-template-columns:1fr;border-top:1px solid #eef2f7}.spec-row .spec-cell::before{content:attr(data-label);display:block;color:#94a3b8;font-size:.64rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.15rem}}
.stats{color:#868e96;font-size:.78rem;margin-top:2rem;padding-top:1rem;border-top:1px solid #e9ecef;text-align:center}
</style>
</head>
<body>
<div class="page-header">
<h1>Design Tokens Preview</h1>
<p class="subtitle">Generated by floop &middot; W3C DTCG format</p>
<!-- NAV -->
</div>
<div class="content">
<!-- SECTIONS -->
<p class="stats"><!-- STATS --></p>
</div>
</body>
</html>
"""


def _px_value(val: str) -> float | None:
    """Extract numeric px value from a dimension string like '16px'."""
    if isinstance(val, str) and val.endswith("px"):
        try:
            return float(val[:-2])
        except ValueError:
            return None
    return None


def _classify_layer(filename: str) -> str:
    """Classify a token filename into a layer name."""
    lower = filename.lower()
    if "global" in lower:
        return "global"
    if "semantic" in lower:
        return "semantic"
    if "component" in lower:
        return "component"
    return filename.replace(".tokens.json", "")


def _collect_groups(data: dict) -> dict[str, str]:
    """Collect top-level group names and their $description."""
    groups: dict[str, str] = {}
    for key, value in data.items():
        if key.startswith("$"):
            continue
        if isinstance(value, dict) and not _is_token_node(value):
            groups[key] = value.get("$description", "")
    return groups


def _build_reference_chain(raw_val: Any, all_tokens: dict[str, dict[str, Any]]) -> list[str]:
    """Follow single-token references and return the ordered chain of token paths."""
    if not isinstance(raw_val, str):
        return []

    chain: list[str] = []
    seen: set[str] = set()
    current = raw_val

    while True:
        refs = _extract_references(current)
        if len(refs) != 1:
            break
        ref = refs[0]
        if ref in seen:
            break
        seen.add(ref)
        chain.append(ref)
        target = all_tokens.get(ref)
        if not isinstance(target, dict):
            break
        current = target.get("$value", "")

    return chain


def _short_name(path: str) -> str:
    """Return the last path segment for compact display."""
    return path.rsplit(".", 1)[-1] if "." in path else path


def _render_token_path(path: str, html_mod: Any) -> str:
    """Render the token path as readable structured segments."""
    segments = [html_mod.escape(part) for part in path.split(".")]
    return f'<div class="path">{" / ".join(segments)}</div>'


def _group_tokens_by_type(
    tokens: list[tuple[str, dict, Any, str, list[str]]]
) -> dict[str, list[tuple[str, dict, Any, str, list[str]]]]:
    """Group token records by their DTCG type."""
    grouped: dict[str, list[tuple[str, dict, Any, str, list[str]]]] = {}
    for record in tokens:
        token_type = record[1].get("$type", "other")
        if token_type not in {"color", "dimension", "fontFamily", "fontWeight"}:
            token_type = "other"
        grouped.setdefault(token_type, []).append(record)
    return grouped


def _pair_color_tokens(
    tokens: list[tuple[str, dict, Any, str, list[str]]]
) -> tuple[
    list[tuple[str, list[tuple[str, dict, Any, str, list[str]]]]],
    list[tuple[str, dict, Any, str, list[str]]],
]:
    """Pair role-based color tokens like primary/on-primary and container variants."""
    by_short = {_short_name(token[0]): token for token in tokens}
    consumed: set[str] = set()
    pairs: list[tuple[str, list[tuple[str, dict, Any, str, list[str]]]]] = []

    for short in sorted(by_short):
        if short in consumed or short.startswith("on-"):
            continue

        pair_records: list[tuple[str, dict, Any, str, list[str]]] = []
        for candidate in (short, f"on-{short}", f"{short}-container", f"on-{short}-container"):
            record = by_short.get(candidate)
            if record is not None:
                pair_records.append(record)

        if len(pair_records) > 1:
            pairs.append((short, pair_records))
            consumed.update(_short_name(path) for path, _, _, _, _ in pair_records)

    leftovers = [token for token in tokens if _short_name(token[0]) not in consumed]
    return pairs, leftovers


def _render_group_tokens(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    """Render a non-component group, splitting mixed token types into sub-sections."""
    grouped = _group_tokens_by_type(tokens)
    ordered_types = [token_type for token_type in _TYPE_ORDER if token_type in grouped]
    parts: list[str] = []

    for index, token_type in enumerate(ordered_types):
        group_tokens = grouped[token_type]
        if len(ordered_types) > 1:
            parts.append('<div class="subgroup">')
            parts.append(
                f'<div class="subgroup-label">{html_mod.escape(_TYPE_LABELS.get(token_type, token_type))}</div>'
            )

        if token_type == "color":
            parts.append(_render_color_group(group_tokens, html_mod))
        elif token_type == "fontFamily":
            parts.append(_render_font_family_group(group_tokens, html_mod))
        elif token_type == "fontWeight":
            parts.append(_render_font_weight_group(group_tokens, html_mod))
        elif token_type == "dimension":
            parts.append(_render_dimension_group(group_tokens, html_mod))
        else:
            parts.append(_render_other_group(group_tokens, html_mod))

        if len(ordered_types) > 1:
            parts.append('</div>')

    return "".join(parts)


def _render_value_pill(node: dict[str, Any], val: Any, html_mod: Any) -> str:
    """Render a compact value pill for spec-style tables."""
    esc_val = html_mod.escape(str(val))
    if node.get("$type") == "color":
        return (
            f'<span class="value-pill"><span class="swatch" style="background:{esc_val}"></span>{esc_val}</span>'
        )
    return f'<span class="value-pill">{esc_val}</span>'


def _render_component_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    """Render component tokens in a spec table inspired by Material component docs."""
    rows: list[str] = [
        '<div class="spec-table">',
        '<div class="spec-head">'
        '<div>Name</div><div>Token ID</div><div>Type</div><div>Reference</div><div>Value</div>'
        '</div>',
    ]

    for path, node, val, ref_str, chain in sorted(tokens, key=lambda item: item[0]):
        short = html_mod.escape(_short_name(path))
        token_id = html_mod.escape(path)
        token_type = html_mod.escape(node.get("$type", "other"))
        desc = node.get("$description", "")
        desc_html = f'<div class="desc">{html_mod.escape(desc)}</div>' if desc else ""
        ref_html = _render_ref(ref_str, html_mod, chain, val) if ref_str else '<span class="value-pill">-</span>'
        rows.append(
            '<div class="spec-row">'
            f'<div class="spec-cell" data-label="Name"><div class="name">{short}</div>{desc_html}</div>'
            f'<div class="spec-cell" data-label="Token ID"><div class="token-id">{token_id}</div>{_render_token_path(path, html_mod)}</div>'
            f'<div class="spec-cell" data-label="Type"><span class="type-pill">{token_type}</span></div>'
            f'<div class="spec-cell" data-label="Reference">{ref_html}</div>'
            f'<div class="spec-cell" data-label="Value">{_render_value_pill(node, val, html_mod)}</div>'
            '</div>'
        )

    rows.append('</div>')
    return ''.join(rows)


def token_view(tokens_dir: Path, out_dir: Path | None = None) -> Path:
    """Generate an HTML preview of all design tokens.

    Reads *.tokens.json files in *tokens_dir*, resolves references,
    groups tokens by source file (layer) and top-level group,
    and writes a visual preview to *out_dir*/design-tokens.html
    (defaults to *tokens_dir* when *out_dir* is not given).

    Returns the path to the generated HTML file.
    """
    import html as html_mod

    # Load all tokens for reference resolution
    all_tokens, resolved = _load_and_resolve_tokens(tokens_dir)

    # Load per-file data for layer grouping
    token_files = sorted(tokens_dir.glob("*.tokens.json"))

    # Structure: layer_name → [(group_name, group_desc, [(path, node, resolved_val, raw_ref, ref_chain)])]
    layers: dict[str, list[tuple[str, str, list[tuple[str, dict, Any, str, list[str]]]]]] = {}
    total_token_count = 0

    for tf in token_files:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue

        layer = _classify_layer(tf.name)
        groups = _collect_groups(data)
        layer_groups: list[tuple[str, str, list[tuple[str, dict, Any, str, list[str]]]]] = []

        # Collect tokens grouped by top-level key
        for key, value in data.items():
            if key.startswith("$") or not isinstance(value, dict):
                continue

            group_desc = groups.get(key, "")
            group_tokens: list[tuple[str, dict, Any, str, list[str]]] = []

            if _is_token_node(value):
                # Top-level token (no group)
                path = key
                raw_val = value.get("$value", "")
                refs = _extract_references(raw_val)
                ref_str = raw_val if refs else ""
                group_tokens.append((path, value, resolved.get(path, raw_val), ref_str, _build_reference_chain(raw_val, all_tokens)))
                total_token_count += 1
            else:
                # Group with nested tokens
                for sub_path, node in _collect_tokens(value, key):
                    raw_val = node.get("$value", "")
                    refs = _extract_references(raw_val)
                    ref_str = raw_val if refs else ""
                    group_tokens.append((sub_path, node, resolved.get(sub_path, raw_val), ref_str, _build_reference_chain(raw_val, all_tokens)))
                    total_token_count += 1

            if group_tokens:
                layer_groups.append((key, group_desc, group_tokens))

        if layer_groups:
            layers[layer] = layer_groups

    # Build HTML sections
    sections: list[str] = []
    nav_links: list[str] = []

    # Sort layers: known layers first by _LAYER_ORDER, then others alphabetically
    sorted_layers = []
    for l in _LAYER_ORDER:
        if l in layers:
            sorted_layers.append(l)
    for l in sorted(layers.keys()):
        if l not in sorted_layers:
            sorted_layers.append(l)

    for layer_name in sorted_layers:
        layer_groups = layers[layer_name]
        meta = _LAYER_META.get(layer_name, {
            "title": html_mod.escape(layer_name.replace("-", " ").replace("_", " ").title()) + " Tokens",
            "subtitle": "",
            "badge_class": "badge-other",
        })

        layer_id = html_mod.escape(layer_name)
        nav_links.append(f'<a href="#{layer_id}">{html_mod.escape(meta["title"])}</a>')

        parts: list[str] = []
        parts.append(f'<div class="layer" id="{layer_id}">')
        parts.append(f'<div class="layer-header">')
        parts.append(f'<h2>{html_mod.escape(meta["title"])}</h2>')
        parts.append(f'<span class="badge {meta["badge_class"]}">{layer_id}</span>')
        parts.append(f'</div>')
        if meta.get("subtitle"):
            parts.append(f'<p class="layer-desc">{html_mod.escape(meta["subtitle"])}</p>')

        for group_name, group_desc, tokens in layer_groups:
            parts.append('<div class="group">')
            gdesc_html = ""
            if group_desc:
                gdesc_html = f'<span class="gdesc">— {html_mod.escape(group_desc)}</span>'
            parts.append(f'<div class="group-title">{html_mod.escape(group_name)} {gdesc_html}</div>')

            if layer_name == "component":
                parts.append(_render_component_group(tokens, html_mod))
            else:
                parts.append(_render_group_tokens(tokens, html_mod))

            parts.append('</div>')

        parts.append('</div>')
        sections.append("\n".join(parts))

    # Navigation
    nav_html = ""
    if nav_links:
        nav_html = f'<div class="nav">{"".join(nav_links)}</div>'

    stats = f"{total_token_count} tokens &middot; {len(layers)} layers &middot; W3C DTCG"
    html_content = _HTML_TEMPLATE.replace(
        "<!-- NAV -->", nav_html
    ).replace(
        "<!-- SECTIONS -->", "\n".join(sections)
    ).replace(
        "<!-- STATS -->", stats
    )

    target_dir = out_dir if out_dir is not None else tokens_dir
    out_path = target_dir / "design-tokens.html"
    out_path.write_text(html_content, encoding="utf-8")

    # Also generate the CSS companion file
    generate_tokens_css(tokens_dir, out_dir=target_dir)

    return out_path


def generate_tokens_css(tokens_dir: Path, out_dir: Path | None = None) -> Path:
    """Generate a CSS custom-properties file from all design tokens.

    Reads *.tokens.json files in *tokens_dir*, resolves references, and writes
    a :root { } block to *out_dir*/tokens.css (defaults to *tokens_dir*).

    Tokens are grouped by layer (global → semantic → component) with comment
    headers so Agent code can reference them directly in HTML ``<link>`` tags.

    Returns the path to the generated CSS file.
    """
    all_tokens, resolved = _load_and_resolve_tokens(tokens_dir)

    # Per-layer token collection: layer_name → [(path, node)]
    token_files = sorted(tokens_dir.glob("*.tokens.json"))
    layer_tokens: dict[str, list[tuple[str, dict]]] = {}
    for tf in token_files:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        layer = _classify_layer(tf.name)
        for path, node in _collect_tokens(data):
            layer_tokens.setdefault(layer, []).append((path, node))

    # Sort layers: known order first, then alphabetical
    ordered: list[str] = []
    for layer in _LAYER_ORDER:
        if layer in layer_tokens:
            ordered.append(layer)
    for layer in sorted(layer_tokens):
        if layer not in ordered:
            ordered.append(layer)

    lines: list[str] = [
        "/* floop Design Tokens — W3C DTCG */",
        "/* DO NOT EDIT — regenerate with: floop token view */",
        ":root {",
    ]
    for layer in ordered:
        meta = _LAYER_META.get(layer, {"title": layer.title() + " Tokens"})
        lines.append(f"  /* ── {meta['title']} ── */")
        for path, node in layer_tokens[layer]:
            css_var = "--" + path.replace(".", "-")
            value = resolved.get(path, node.get("$value", ""))
            lines.append(f"  {css_var}: {value};")
        lines.append("")

    # Remove trailing blank line before closing brace
    if lines and lines[-1] == "":
        lines.pop()
    lines.append("}")

    target_dir = out_dir if out_dir is not None else tokens_dir
    css_path = target_dir / "tokens.css"
    css_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return css_path


# ---------------------------------------------------------------------------
# Render helpers for each token type
# ---------------------------------------------------------------------------

def _render_ref(
    ref_str: str,
    html_mod: Any,
    chain: list[str] | None = None,
    resolved_val: Any | None = None,
) -> str:
    """Render a reference string as a small annotation."""
    if not ref_str:
        return ""
    parts = [f'<div class="ref">\u2192 {html_mod.escape(ref_str)}</div>']
    if chain:
        chain_text = " &rarr; ".join(html_mod.escape(item) for item in chain)
        resolved_html = ""
        if resolved_val is not None:
            resolved_html = f' <span class="resolved">= {html_mod.escape(str(resolved_val))}</span>'
        parts.append(f'<div class="chain">Chain: {chain_text}{resolved_html}</div>')
    return ''.join(parts)


def _render_color_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    pairs, leftovers = _pair_color_tokens(tokens)
    sections: list[str] = []

    if pairs:
        pair_cards: list[str] = []
        for title, pair_tokens in pairs:
            rows: list[str] = []
            for path, node, val, ref_str, chain in pair_tokens:
                esc_val = html_mod.escape(str(val))
                rows.append(
                    '<div class="color-pair-row">'
                    '<div class="meta">'
                    f'<div class="name">{html_mod.escape(_short_name(path))}</div>'
                    f'<div class="value">{esc_val}</div>'
                    f'{_render_token_path(path, html_mod)}'
                    f'{_render_ref(ref_str, html_mod, chain, val)}'
                    '</div>'
                    f'<div class="color-chip"><span class="dot" style="background:{esc_val}"></span>{esc_val}</div>'
                    '</div>'
                )
            pair_cards.append(
                f'<div class="color-pair"><div class="color-pair-title">{html_mod.escape(title)}</div>{"".join(rows)}</div>'
            )
        sections.append(f'<div class="color-pair-grid">{"".join(pair_cards)}</div>')

    cards: list[str] = []
    for path, node, val, ref_str, chain in leftovers:
        desc = node.get("$description", "")
        esc_val = html_mod.escape(str(val))
        short = _short_name(path)
        esc_short = html_mod.escape(short)
        esc_path = html_mod.escape(path)
        cards.append(
            (
                f'<div class="swatch" title="{esc_path}">'
                f'<div class="swatch-color" style="background:{esc_val}"></div>'
                f'<div class="swatch-info">'
                f'<div class="name">{esc_short}</div>'
                + _render_token_path(path, html_mod)
                + f'<div class="value">{esc_val}</div>'
                + _render_ref(ref_str, html_mod, chain, val)
                + (f'<div class="desc">{html_mod.escape(desc)}</div>' if desc else "")
                + "</div></div>"
            )
        )
    if cards:
        sections.append(f'<div class="grid">{"".join(cards)}</div>')
    return f'<div class="color-stack">{"".join(sections)}</div>' if sections else ''


def _render_dimension_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    cards: list[str] = []
    for path, node, val, ref_str, chain in tokens:
        esc_val = html_mod.escape(str(val))
        short = _short_name(path)
        esc_short = html_mod.escape(short)
        px = _px_value(str(val))
        bar = ""
        if px is not None:
            clamped = min(px, 200)
            bar = f'<div class="bar" style="width:{clamped}px"></div>'
        cards.append(
            (
                f'<div class="dim-item">'
                f'<span class="name">{esc_short}</span>'
                + _render_token_path(path, html_mod)
                + f'<span class="value">{esc_val}</span>'
                + _render_ref(ref_str, html_mod, chain, val)
                + f"{bar}</div>"
            )
        )
    return f'<div class="dim-grid">{"".join(cards)}</div>'


def _render_font_family_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    cards: list[str] = []
    for path, node, val, ref_str, chain in tokens:
        esc_val = html_mod.escape(str(val))
        short = _short_name(path)
        esc_short = html_mod.escape(short)
        cards.append(
            (
                f'<div class="font-sample">'
                f'<div class="name">{esc_short}</div>'
                + _render_token_path(path, html_mod)
                + f'<div class="value">{esc_val}</div>'
                + _render_ref(ref_str, html_mod, chain, val)
                + f'<div class="preview" style="font-family:{esc_val}">'
                + "The quick brown fox jumps over the lazy dog</div></div>"
            )
        )
    return "".join(cards)


def _render_font_weight_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    cards: list[str] = []
    for path, node, val, ref_str, chain in tokens:
        esc_val = html_mod.escape(str(val))
        short = _short_name(path)
        esc_short = html_mod.escape(short)
        cards.append(
            (
                f'<div class="weight-sample">'
                f'<div class="name">{esc_short}</div>'
                + _render_token_path(path, html_mod)
                + f'<div class="value">{esc_val}</div>'
                + _render_ref(ref_str, html_mod, chain, val)
                + f'<div class="preview" style="font-weight:{esc_val}">Aa</div></div>'
            )
        )
    return f'<div class="weight-grid">{"".join(cards)}</div>'


def _render_other_group(
    tokens: list[tuple[str, dict, Any, str, list[str]]], html_mod: Any
) -> str:
    cards: list[str] = []
    for path, node, val, ref_str, chain in tokens:
        esc_val = html_mod.escape(str(val))
        short = _short_name(path)
        esc_short = html_mod.escape(short)
        cards.append(
            (
                f'<div class="other-item">'
                f'<span class="name">{esc_short}</span>'
                + _render_token_path(path, html_mod)
                + f'<span class="value">{esc_val}</span>'
                + _render_ref(ref_str, html_mod, chain, val)
                + "</div>"
            )
        )
    return f'<div class="dim-grid">{"".join(cards)}</div>'
