"""Tests for floop.tokens — W3C DTCG token management."""

import json
from pathlib import Path

import pytest

from floop.tokens import (
    COMPONENT_TOKENS,
    DTCG_TYPES,
    GLOBAL_TOKENS,
    RECOMMENDED_SEMANTIC_TOKENS,
    SEMANTIC_TOKENS,
    _build_reference_chain,
    _classify_layer,
    _collect_all_paths,
    _collect_groups,
    _collect_tokens,
    _detect_circular_refs,
    _extract_references,
    _is_group_node,
    _is_token_node,
    _load_and_resolve_tokens,
    _pair_color_tokens,
    _px_value,
    _render_ref,
    _resolve_value,
    generate_tokens_css,
    token_init,
    token_validate,
    token_view,
)


# ---------------------------------------------------------------------------
# Template constants sanity checks
# ---------------------------------------------------------------------------


class TestTemplateConstants:
    def test_dtcg_types_contains_core_types(self):
        for t in ("color", "dimension", "fontFamily", "fontWeight", "shadow", "border"):
            assert t in DTCG_TYPES

    def test_global_tokens_not_empty(self):
        assert len(GLOBAL_TOKENS) > 0

    def test_semantic_tokens_not_empty(self):
        assert len(SEMANTIC_TOKENS) > 0

    def test_component_tokens_not_empty(self):
        assert len(COMPONENT_TOKENS) > 0

    def test_recommended_semantic_tokens_has_entries(self):
        assert "color" in RECOMMENDED_SEMANTIC_TOKENS
        assert len(RECOMMENDED_SEMANTIC_TOKENS["color"]) > 0


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestIsTokenNode:
    def test_token_with_value(self):
        assert _is_token_node({"$type": "color", "$value": "#fff"}) is True

    def test_group_without_value(self):
        assert _is_token_node({"nested": {"$value": "x"}}) is False

    def test_empty_dict(self):
        assert _is_token_node({}) is False


class TestIsGroupNode:
    def test_group_with_nested_dicts(self):
        assert _is_group_node({"child": {"$value": "x"}}) is True

    def test_token_node_is_not_group(self):
        assert _is_group_node({"$value": "#000", "$type": "color"}) is False

    def test_dict_with_only_scalars(self):
        assert _is_group_node({"$description": "test"}) is False

    def test_empty_dict(self):
        assert _is_group_node({}) is False


class TestCollectTokens:
    def test_flat_tokens(self):
        data = {
            "red": {"$type": "color", "$value": "#f00"},
            "blue": {"$type": "color", "$value": "#00f"},
        }
        result = _collect_tokens(data)
        paths = [p for p, _ in result]
        assert "red" in paths
        assert "blue" in paths

    def test_nested_group(self):
        data = {
            "color": {
                "primary": {"$type": "color", "$value": "#000"},
            }
        }
        result = _collect_tokens(data)
        assert result[0][0] == "color.primary"

    def test_skips_dollar_keys(self):
        data = {
            "$description": "Top level",
            "token": {"$type": "color", "$value": "#fff"},
        }
        result = _collect_tokens(data)
        assert len(result) == 1
        assert result[0][0] == "token"

    def test_deeply_nested(self):
        data = {
            "a": {"b": {"c": {"$type": "color", "$value": "#123"}}}
        }
        result = _collect_tokens(data)
        assert result[0][0] == "a.b.c"

    def test_with_prefix(self):
        data = {"x": {"$type": "color", "$value": "#abc"}}
        result = _collect_tokens(data, prefix="root")
        assert result[0][0] == "root.x"


class TestExtractReferences:
    def test_single_reference(self):
        assert _extract_references("{color.blue-500}") == ["color.blue-500"]

    def test_multiple_references(self):
        refs = _extract_references("{a.b} and {c.d}")
        assert refs == ["a.b", "c.d"]

    def test_no_references(self):
        assert _extract_references("#ffffff") == []

    def test_non_string_value(self):
        assert _extract_references(400) == []

    def test_empty_string(self):
        assert _extract_references("") == []


class TestCollectAllPaths:
    def test_collects_groups_and_tokens(self):
        data = {
            "color": {
                "primary": {"$type": "color", "$value": "#000"},
            }
        }
        paths = _collect_all_paths(data)
        assert "color" in paths
        assert "color.primary" in paths

    def test_skips_dollar_keys(self):
        data = {
            "$description": "ignored",
            "token": {"$type": "color", "$value": "#fff"},
        }
        paths = _collect_all_paths(data)
        assert "token" in paths
        assert "$description" not in paths


class TestDetectCircularRefs:
    def test_no_cycles(self):
        tokens = {
            "a": {"$value": "{b}"},
            "b": {"$value": "#fff"},
        }
        cycles = _detect_circular_refs(tokens)
        assert cycles == []

    def test_simple_cycle(self):
        tokens = {
            "a": {"$value": "{b}"},
            "b": {"$value": "{a}"},
        }
        cycles = _detect_circular_refs(tokens)
        assert len(cycles) > 0

    def test_self_reference(self):
        tokens = {
            "a": {"$value": "{a}"},
        }
        cycles = _detect_circular_refs(tokens)
        assert len(cycles) > 0

    def test_three_node_cycle(self):
        tokens = {
            "a": {"$value": "{b}"},
            "b": {"$value": "{c}"},
            "c": {"$value": "{a}"},
        }
        cycles = _detect_circular_refs(tokens)
        assert len(cycles) > 0


# ---------------------------------------------------------------------------
# token_init
# ---------------------------------------------------------------------------


class TestTokenInit:
    def test_creates_three_files(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        created = token_init(tokens_dir)
        assert len(created) == 3
        names = {p.name for p in created}
        assert names == {"global.tokens.json", "semantic.tokens.json", "component.tokens.json"}

    def test_files_are_valid_json(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        for f in tokens_dir.glob("*.tokens.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            assert isinstance(data, dict)

    def test_creates_directory_if_not_exists(self, tmp_path):
        tokens_dir = tmp_path / "deep" / "nested" / "tokens"
        assert not tokens_dir.exists()
        token_init(tokens_dir)
        assert tokens_dir.exists()

    def test_global_tokens_have_valid_types(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        data = json.loads((tokens_dir / "global.tokens.json").read_text(encoding="utf-8"))
        tokens = _collect_tokens(data)
        for _, node in tokens:
            assert node.get("$type") in DTCG_TYPES

    def test_semantic_tokens_reference_global(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        data = json.loads((tokens_dir / "semantic.tokens.json").read_text(encoding="utf-8"))
        tokens = _collect_tokens(data)
        has_ref = any(_extract_references(n.get("$value", "")) for _, n in tokens)
        assert has_ref, "semantic tokens should reference global tokens"

    def test_component_tokens_reference_semantic(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        data = json.loads((tokens_dir / "component.tokens.json").read_text(encoding="utf-8"))
        tokens = _collect_tokens(data)
        has_ref = any(_extract_references(n.get("$value", "")) for _, n in tokens)
        assert has_ref, "component tokens should reference semantic tokens"


# ---------------------------------------------------------------------------
# token_validate
# ---------------------------------------------------------------------------


class TestTokenValidate:
    def test_valid_default_tokens(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        result = token_validate(tokens_dir)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["stats"]["files"] == 3
        assert result["stats"]["tokens"] > 0
        assert result["stats"]["references"] > 0

    def test_no_token_files(self, tmp_path):
        tokens_dir = tmp_path / "empty"
        tokens_dir.mkdir()
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "NO_TOKEN_FILES" for e in result["errors"])

    def test_invalid_json(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "bad.tokens.json").write_text("{invalid", encoding="utf-8")
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "INVALID_JSON" for e in result["errors"])

    def test_root_not_object(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "array.tokens.json").write_text("[]", encoding="utf-8")
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "NOT_OBJECT" for e in result["errors"])

    def test_invalid_type(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"bad": {"$type": "notAType", "$value": "x"}}
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "INVALID_TYPE" for e in result["errors"])

    def test_missing_value(self, tmp_path):
        """A node with $type but no $value is treated as a group (not a token).
        DTCG spec: $value is what makes a node a token. No $value = group node."""
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        # A node with $type only is a group, not a token — no error expected
        data = {"bad": {"$type": "color"}}
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        # No token found → valid (just empty), but warnings for missing recommended
        assert result["stats"]["tokens"] == 0

    def test_broken_reference(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "ref": {"$type": "color", "$value": "{nonexistent.token}"},
        }
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "BROKEN_REFERENCE" for e in result["errors"])

    def test_circular_reference(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "a": {"$type": "color", "$value": "{b}"},
            "b": {"$type": "color", "$value": "{a}"},
        }
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        assert result["valid"] is False
        assert any(e["code"] == "CIRCULAR_REFERENCE" for e in result["errors"])

    def test_missing_recommended_tokens_warning(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        # Minimal valid file with no recommended semantic tokens
        data = {"custom": {"$type": "color", "$value": "#000"}}
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        assert any(w["code"] == "MISSING_RECOMMENDED" for w in result["warnings"])

    def test_valid_with_no_warnings_possible(self, tmp_path):
        """When all recommended tokens are present, no MISSING_RECOMMENDED warnings."""
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        result = token_validate(tokens_dir)
        missing_rec = [w for w in result["warnings"] if w["code"] == "MISSING_RECOMMENDED"]
        assert len(missing_rec) == 0

    def test_stats_counts(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "$description": "Top-level metadata (should be skipped in group count)",
            "color": {
                "red": {"$type": "color", "$value": "#f00"},
                "blue": {"$type": "color", "$value": "#00f"},
            }
        }
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        assert result["stats"]["files"] == 1
        assert result["stats"]["tokens"] == 2
        assert result["stats"]["groups"] == 1  # "color" group, "$description" skipped

    def test_token_without_type_is_valid(self, tmp_path):
        """$type is optional per DTCG — no error if missing."""
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"x": {"$value": "16px"}}
        (tokens_dir / "test.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = token_validate(tokens_dir)
        type_errors = [e for e in result["errors"] if e["code"] == "INVALID_TYPE"]
        assert len(type_errors) == 0

    def test_cross_file_reference(self, tmp_path):
        """References can resolve across files."""
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        global_data = {"color": {"red": {"$type": "color", "$value": "#f00"}}}
        semantic_data = {"primary": {"$type": "color", "$value": "{color.red}"}}
        (tokens_dir / "global.tokens.json").write_text(json.dumps(global_data), encoding="utf-8")
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(semantic_data), encoding="utf-8")
        result = token_validate(tokens_dir)
        ref_errors = [e for e in result["errors"] if e["code"] == "BROKEN_REFERENCE"]
        assert len(ref_errors) == 0

    def test_suggestion_field_present(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"bad": {"$type": "fakeType", "$value": "x"}}
        (tokens_dir / "test.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        result = token_validate(tokens_dir)
        for err in result["errors"]:
            assert "suggestion" in err


# ---------------------------------------------------------------------------
# _resolve_value / _load_and_resolve_tokens / _px_value
# ---------------------------------------------------------------------------


class TestResolveValue:
    def test_resolve_no_refs(self):
        result = _resolve_value("#fff", {})
        assert result == "#fff"

    def test_resolve_single_ref(self):
        all_tokens = {"color.red": {"$value": "#f00"}}
        result = _resolve_value("{color.red}", all_tokens)
        assert result == "#f00"

    def test_resolve_chained_refs(self):
        all_tokens = {
            "color.red": {"$value": "#f00"},
            "color.primary": {"$value": "{color.red}"},
        }
        result = _resolve_value("{color.primary}", all_tokens)
        assert result == "#f00"

    def test_resolve_circular_stops(self):
        all_tokens = {
            "a": {"$value": "{b}"},
            "b": {"$value": "{a}"},
        }
        # Should not infinite-loop; returns partially resolved
        result = _resolve_value("{a}", all_tokens)
        assert isinstance(result, str)

    def test_resolve_non_string(self):
        result = _resolve_value(400, {})
        assert result == 400

    def test_resolve_unknown_ref_kept(self):
        result = _resolve_value("{unknown.ref}", {})
        assert result == "{unknown.ref}"


class TestPxValue:
    def test_valid_px(self):
        assert _px_value("16px") == 16.0

    def test_float_px(self):
        assert _px_value("4.5px") == 4.5

    def test_non_px(self):
        assert _px_value("1rem") is None

    def test_non_string(self):
        assert _px_value(42) is None

    def test_invalid_number(self):
        assert _px_value("abcpx") is None


class TestLoadAndResolve:
    def test_resolves_across_files(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        all_tokens, resolved = _load_and_resolve_tokens(tokens_dir)
        # Semantic token "color.primary" should resolve to a hex value
        assert "color.primary" in resolved
        assert resolved["color.primary"].startswith("#")

    def test_skips_invalid_json(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "bad.tokens.json").write_text("{invalid", encoding="utf-8")
        (tokens_dir / "good.tokens.json").write_text(
            json.dumps({"x": {"$type": "color", "$value": "#000"}}),
            encoding="utf-8",
        )
        all_tokens, resolved = _load_and_resolve_tokens(tokens_dir)
        assert "x" in resolved

    def test_skips_non_object_root(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "arr.tokens.json").write_text("[]", encoding="utf-8")
        all_tokens, resolved = _load_and_resolve_tokens(tokens_dir)
        assert len(all_tokens) == 0


# ---------------------------------------------------------------------------
# token_view
# ---------------------------------------------------------------------------


class TestTokenView:
    def test_generates_html_file(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        out = token_view(tokens_dir)
        assert out.name == "design-tokens.html"
        assert out.exists()

    def test_out_dir_overrides_output_location(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        out_dir = tmp_path / "build"
        out_dir.mkdir()
        token_init(tokens_dir)
        out = token_view(tokens_dir, out_dir=out_dir)
        assert out == out_dir / "design-tokens.html"
        assert out.exists()
        assert not (tokens_dir / "design-tokens.html").exists()

    def test_html_contains_colors(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert "Global Tokens" in html
        assert "#2563EB" in html  # blue-500

    def test_html_contains_dimensions(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert "spacing" in html  # spacing group in global tokens
        assert "16px" in html

    def test_html_contains_font_families(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert "fontFamily" in html  # group name
        assert "Inter" in html

    def test_html_contains_font_weights(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert "fontWeight" in html  # group name
        assert "400" in html

    def test_html_has_doctype(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>")

    def test_html_contains_stats(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        html = (tokens_dir / "design-tokens.html").read_text(encoding="utf-8")
        assert "tokens" in html
        assert "layers" in html
        assert "W3C DTCG" in html

    def test_other_type_rendered(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"dur": {"$type": "duration", "$value": "200ms"}}
        (tokens_dir / "misc.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        out = token_view(tokens_dir)
        html = out.read_text(encoding="utf-8")
        assert "Misc Tokens" in html
        assert "200ms" in html

    def test_html_escapes_values(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"x": {"$type": "color", "$value": "<script>alert(1)</script>"}}
        (tokens_dir / "xss.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        out = token_view(tokens_dir)
        html = out.read_text(encoding="utf-8")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_description_shown(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"red": {"$type": "color", "$value": "#f00", "$description": "Error red"}}
        (tokens_dir / "desc.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        out = token_view(tokens_dir)
        html = out.read_text(encoding="utf-8")
        assert "Error red" in html

    def test_dimension_bar_rendered(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"gap": {"$type": "dimension", "$value": "16px"}}
        (tokens_dir / "dim.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        out = token_view(tokens_dir)
        html = out.read_text(encoding="utf-8")
        assert 'class="bar"' in html

    def test_empty_tokens_dir(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        # No token files → still generates HTML but with no sections
        out = token_view(tokens_dir)
        html = out.read_text(encoding="utf-8")
        assert "0 tokens" in html
        assert "0 layers" in html

    def test_skips_invalid_json_in_view(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "bad.tokens.json").write_text("not json", encoding="utf-8")
        (tokens_dir / "good.tokens.json").write_text(
            json.dumps({"c": {"$type": "color", "$value": "#000"}}),
            encoding="utf-8",
        )
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "#000" in html  # good file processed
        assert "1 tokens" in html

    def test_skips_non_dict_root_in_view(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        (tokens_dir / "arr.tokens.json").write_text("[1,2]", encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "0 tokens" in html

    def test_skips_non_dict_values_in_file(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"$version": "1.0", "note": "just a string", "c": {"$type": "color", "$value": "#abc"}}
        (tokens_dir / "mixed.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "#abc" in html
        assert "1 tokens" in html

    def test_reference_arrow_shown(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        g = {"brand": {"$type": "color", "$value": "#f00"}}
        s = {"primary": {"$type": "color", "$value": "{brand}"}}
        (tokens_dir / "global.tokens.json").write_text(json.dumps(g), encoding="utf-8")
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(s), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "→" in html  # reference arrow
        assert "{brand}" in html

    def test_layer_navigation(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="nav"' in html
        assert "#global" in html
        assert "#semantic" in html
        assert "#component" in html

    def test_group_description_in_view(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "brand": {
                "$description": "Brand palette",
                "red": {"$type": "color", "$value": "#f00"},
            }
        }
        (tokens_dir / "global.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "Brand palette" in html

    def test_component_group_renders_specs_table(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="spec-table"' in html
        assert "Token ID" in html
        assert "button.background" in html

    def test_mixed_group_splits_types(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "font": {
                "$description": "Mixed font group",
                "body": {"$type": "fontFamily", "$value": "Inter, sans-serif"},
                "size-body": {"$type": "dimension", "$value": "16px"},
            }
        }
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "Font Family" in html
        assert "Dimensions" in html
        assert 'class="font-sample"' in html
        assert 'class="dim-item"' in html

    def test_full_reference_chain_shown(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        global_data = {"color": {"brand": {"$type": "color", "$value": "#112233"}}}
        semantic_data = {"color": {"primary": {"$type": "color", "$value": "{color.brand}"}}}
        component_data = {"button": {"background": {"$type": "color", "$value": "{color.primary}"}}}
        (tokens_dir / "global.tokens.json").write_text(json.dumps(global_data), encoding="utf-8")
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(semantic_data), encoding="utf-8")
        (tokens_dir / "component.tokens.json").write_text(json.dumps(component_data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "Chain:" in html
        assert "color.primary" in html
        assert "color.brand" in html
        assert "#112233" in html

    def test_color_roles_paired_when_available(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "color": {
                "primary": {"$type": "color", "$value": "#111111"},
                "on-primary": {"$type": "color", "$value": "#ffffff"},
                "primary-container": {"$type": "color", "$value": "#dddddd"},
                "on-primary-container": {"$type": "color", "$value": "#000000"},
            }
        }
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="color-pair-grid"' in html
        assert "on-primary" in html
        assert "primary-container" in html


# ---------------------------------------------------------------------------
# _classify_layer
# ---------------------------------------------------------------------------

class TestClassifyLayer:
    def test_global(self):
        assert _classify_layer("global.tokens.json") == "global"

    def test_semantic(self):
        assert _classify_layer("semantic.tokens.json") == "semantic"

    def test_component(self):
        assert _classify_layer("component.tokens.json") == "component"

    def test_unknown_uses_stem(self):
        assert _classify_layer("brand.tokens.json") == "brand"

    def test_case_insensitive(self):
        assert _classify_layer("Global.tokens.json") == "global"


# ---------------------------------------------------------------------------
# _collect_groups
# ---------------------------------------------------------------------------

class TestCollectGroups:
    def test_extracts_groups_with_description(self):
        data = {
            "$description": "top level",
            "color": {
                "$description": "Color palette",
                "red": {"$type": "color", "$value": "#f00"},
            },
            "spacing": {
                "sm": {"$type": "dimension", "$value": "4px"},
            },
        }
        result = _collect_groups(data)
        assert result == {"color": "Color palette", "spacing": ""}

    def test_skips_dollar_keys(self):
        data = {"$type": "color", "red": {"$type": "color", "$value": "#f00"}}
        result = _collect_groups(data)
        # "red" is a token node, not a group
        assert result == {}

    def test_empty_dict(self):
        assert _collect_groups({}) == {}


# ---------------------------------------------------------------------------
# _render_ref
# ---------------------------------------------------------------------------

class TestRenderRef:
    def test_empty_ref(self):
        import html as html_mod
        assert _render_ref("", html_mod) == ""

    def test_with_ref(self):
        import html as html_mod
        result = _render_ref("{color.primary}", html_mod)
        assert "→" in result
        assert "{color.primary}" in result
        assert 'class="ref"' in result

    def test_escapes_html(self):
        import html as html_mod
        result = _render_ref("<script>", html_mod)
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_chain_rendered(self):
        import html as html_mod
        result = _render_ref("{a.b}", html_mod, chain=["a.b", "ref.raw"], resolved_val="#fff")
        assert 'class="chain"' in result
        assert "a.b" in result
        assert "#fff" in result


# ---------------------------------------------------------------------------
# _build_reference_chain
# ---------------------------------------------------------------------------

class TestBuildReferenceChain:
    def test_no_reference_returns_empty(self):
        tokens = {"a": {"$type": "color", "$value": "#f00"}}
        assert _build_reference_chain("#f00", tokens) == []

    def test_single_hop(self):
        tokens = {"base": {"$type": "color", "$value": "#00f"}}
        result = _build_reference_chain("{base}", tokens)
        assert result == ["base"]

    def test_two_hop_chain(self):
        tokens = {
            "primitive": {"$type": "color", "$value": "#abc"},
            "alias": {"$type": "color", "$value": "{primitive}"},
        }
        result = _build_reference_chain("{alias}", tokens)
        assert result == ["alias", "primitive"]

    def test_circular_ref_stops(self):
        # a -> b -> a (circular) — must not loop forever, covers L834
        tokens = {
            "a": {"$type": "color", "$value": "{b}"},
            "b": {"$type": "color", "$value": "{a}"},
        }
        result = _build_reference_chain("{a}", tokens)
        assert "a" in result
        assert "b" in result
        assert len(result) == 2  # stops at the cycle, no infinite loop

    def test_missing_target_stops(self):
        # Reference points to a nonexistent key — covers L839
        tokens = {}
        result = _build_reference_chain("{missing.token}", tokens)
        assert result == ["missing.token"]

    def test_non_string_value_returns_empty(self):
        assert _build_reference_chain(42, {}) == []  # type: ignore[arg-type]

    def test_multi_reference_stops(self):
        # Value contains multiple refs — not a single chain, stops immediately
        tokens = {"a": {"$value": "#f"}, "b": {"$value": "#0"}}
        result = _build_reference_chain("{a} {b}", tokens)
        assert result == []


# ---------------------------------------------------------------------------
# _pair_color_tokens
# ---------------------------------------------------------------------------

class TestPairColorTokens:
    def _make_token(self, path: str, val: str = "#fff"):
        return (path, {"$type": "color", "$value": val}, val, "", [])

    def test_pairs_primary_set(self):
        tokens = [
            self._make_token("color.primary", "#00f"),
            self._make_token("color.on-primary", "#fff"),
            self._make_token("color.primary-container", "#ccf"),
            self._make_token("color.on-primary-container", "#001"),
        ]
        pairs, leftovers = _pair_color_tokens(tokens)
        assert len(pairs) == 1
        assert pairs[0][0] == "primary"
        assert len(pairs[0][1]) == 4
        assert leftovers == []

    def test_standalone_tokens_are_leftovers(self):
        tokens = [
            self._make_token("color.brand", "#f00"),
            self._make_token("color.logo", "#0f0"),
        ]
        pairs, leftovers = _pair_color_tokens(tokens)
        assert pairs == []
        assert len(leftovers) == 2

    def test_partial_pair_two_members(self):
        # Only primary + on-primary (no container variants)
        tokens = [
            self._make_token("color.surface", "#fff"),
            self._make_token("color.on-surface", "#000"),
        ]
        pairs, leftovers = _pair_color_tokens(tokens)
        assert len(pairs) == 1
        assert len(pairs[0][1]) == 2
        assert leftovers == []

    def test_on_only_not_a_pair_initiator(self):
        # on-* alone should not start a new pair group
        tokens = [self._make_token("color.on-error", "#fff")]
        pairs, leftovers = _pair_color_tokens(tokens)
        assert pairs == []
        assert len(leftovers) == 1


# ---------------------------------------------------------------------------
# Component spec table rendering (via token_view)
# ---------------------------------------------------------------------------

class TestComponentSpecTable:
    def test_spec_table_rendered_for_component_layer(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "button": {
                "$description": "Button tokens",
                "bg": {"$type": "color", "$value": "{color.primary}"},
            }
        }
        (tokens_dir / "component.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="spec-table"' in html
        assert 'class="spec-head"' in html
        assert "Token ID" in html

    def test_spec_table_shows_token_id(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"btn": {"bg": {"$type": "color", "$value": "#000"}}}
        (tokens_dir / "component.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "btn.bg" in html

    def test_spec_table_shows_reference_chain(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        g = {"brand": {"$type": "color", "$value": "#f00"}}
        c = {"button": {"bg": {"$type": "color", "$value": "{brand}"}}}
        (tokens_dir / "global.tokens.json").write_text(json.dumps(g), encoding="utf-8")
        (tokens_dir / "component.tokens.json").write_text(json.dumps(c), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert "{brand}" in html
        assert "#f00" in html

    def test_global_layer_uses_swatches_not_spec_table(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"col": {"red": {"$type": "color", "$value": "#f00"}}}
        (tokens_dir / "global.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="swatch"' in html
        assert 'class="spec-table"' not in html


# ---------------------------------------------------------------------------
# Color pairing in HTML output
# ---------------------------------------------------------------------------

class TestColorPairingInView:
    def test_paired_colors_rendered_as_pair_grid(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "color": {
                "primary": {"$type": "color", "$value": "#00f"},
                "on-primary": {"$type": "color", "$value": "#fff"},
            }
        }
        (tokens_dir / "global.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="color-pair-grid"' in html
        assert 'class="color-pair"' in html

    def test_unpaired_colors_rendered_as_swatches(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "color": {
                "brand-red": {"$type": "color", "$value": "#f00"},
                "brand-blue": {"$type": "color", "$value": "#00f"},
            }
        }
        (tokens_dir / "global.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="swatch"' in html

    def test_mixed_type_group_shows_subgroup_labels(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {
            "brand": {
                "primary": {"$type": "color", "$value": "#00f"},
                "spacing": {"$type": "dimension", "$value": "8px"},
            }
        }
        (tokens_dir / "global.tokens.json").write_text(json.dumps(data), encoding="utf-8")
        html = token_view(tokens_dir).read_text(encoding="utf-8")
        assert 'class="subgroup-label"' in html
        assert "Colors" in html
        assert "Dimensions" in html


# ---------------------------------------------------------------------------
# generate_tokens_css
# ---------------------------------------------------------------------------


class TestGenerateTokensCss:
    def test_generates_css_file(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        css_path = generate_tokens_css(tokens_dir)
        assert css_path.name == "tokens.css"
        assert css_path.exists()

    def test_out_dir_overrides_location(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        out_dir = tmp_path / "build"
        out_dir.mkdir()
        token_init(tokens_dir)
        css_path = generate_tokens_css(tokens_dir, out_dir=out_dir)
        assert css_path == out_dir / "tokens.css"
        assert css_path.exists()
        assert not (tokens_dir / "tokens.css").exists()

    def test_contains_root_block(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        assert ":root {" in css
        assert "}" in css

    def test_contains_css_custom_properties(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        # global token color.blue-500 -> --color-blue-500
        assert "--color-blue-500:" in css
        assert "#2563EB" in css

    def test_token_path_uses_dashes(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        data = {"button": {"primary-bg": {"$type": "color", "$value": "#ff0000"}}}
        (tokens_dir / "component.tokens.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        assert "--button-primary-bg: #ff0000;" in css

    def test_references_resolved_to_concrete_values(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        g = {"brand": {"$type": "color", "$value": "#123456"}}
        s = {"primary": {"$type": "color", "$value": "{brand}"}}
        (tokens_dir / "global.tokens.json").write_text(json.dumps(g), encoding="utf-8")
        (tokens_dir / "semantic.tokens.json").write_text(json.dumps(s), encoding="utf-8")
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        # semantic.primary should resolve to #123456, not {brand}
        assert "--primary: #123456;" in css

    def test_layer_comment_headers_present(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        assert "Global Tokens" in css
        assert "Semantic Tokens" in css
        assert "Component Tokens" in css

    def test_do_not_edit_header_present(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        assert "DO NOT EDIT" in css
        assert "floop token view" in css

    def test_empty_tokens_dir_produces_root_block(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        css = generate_tokens_css(tokens_dir).read_text(encoding="utf-8")
        assert ":root {" in css

    def test_token_view_also_writes_css(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        token_init(tokens_dir)
        token_view(tokens_dir)
        assert (tokens_dir / "tokens.css").exists()

    def test_token_view_css_in_out_dir(self, tmp_path):
        tokens_dir = tmp_path / "tokens"
        out_dir = tmp_path / "build"
        out_dir.mkdir()
        token_init(tokens_dir)
        token_view(tokens_dir, out_dir=out_dir)
        assert (out_dir / "tokens.css").exists()
        assert not (tokens_dir / "tokens.css").exists()
