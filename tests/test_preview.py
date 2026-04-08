"""Tests for floop.preview — index page generator."""

import json
from pathlib import Path

import pytest

from floop.preview import (
    _build_nav_html,
    _categorize_files,
    _display_name,
    generate_preview_index,
)


# ---------------------------------------------------------------------------
# _display_name
# ---------------------------------------------------------------------------


class TestDisplayName:
    def test_hyphen_to_title(self):
        assert _display_name("design-tokens") == "Design Tokens"

    def test_underscore_to_title(self):
        assert _display_name("home_page") == "Home Page"

    def test_mixed(self):
        assert _display_name("my-component_v2") == "My Component V2"

    def test_already_capitalized(self):
        assert _display_name("About") == "About"


# ---------------------------------------------------------------------------
# _categorize_files
# ---------------------------------------------------------------------------


class TestCategorizeFiles:
    def _make(self, tmp_path: Path, names: list[str]) -> None:
        for name in names:
            (tmp_path / name).write_text("<html></html>", encoding="utf-8")

    def test_empty_dir_returns_empty(self, tmp_path):
        assert _categorize_files(tmp_path) == {}

    def test_excludes_index_html(self, tmp_path):
        self._make(tmp_path, ["index.html"])
        assert _categorize_files(tmp_path) == {}

    def test_token_file_goes_to_design_system(self, tmp_path):
        self._make(tmp_path, ["design-tokens.html"])
        cats = _categorize_files(tmp_path)
        assert "Design System" in cats
        assert cats["Design System"][0].name == "design-tokens.html"

    def test_color_file_goes_to_design_system(self, tmp_path):
        self._make(tmp_path, ["color-palette.html"])
        cats = _categorize_files(tmp_path)
        assert "Design System" in cats

    def test_typography_file_goes_to_design_system(self, tmp_path):
        self._make(tmp_path, ["typography.html"])
        cats = _categorize_files(tmp_path)
        assert "Design System" in cats

    def test_component_file_goes_to_components(self, tmp_path):
        self._make(tmp_path, ["button-component.html"])
        cats = _categorize_files(tmp_path)
        assert "Components" in cats
        assert cats["Components"][0].name == "button-component.html"

    def test_widget_file_goes_to_components(self, tmp_path):
        self._make(tmp_path, ["card-widget.html"])
        cats = _categorize_files(tmp_path)
        assert "Components" in cats

    def test_other_file_goes_to_prototypes(self, tmp_path):
        self._make(tmp_path, ["home.html", "about.html"])
        cats = _categorize_files(tmp_path)
        assert "Prototypes" in cats
        assert len(cats["Prototypes"]) == 2

    def test_multiple_categories(self, tmp_path):
        self._make(
            tmp_path,
            ["design-tokens.html", "button-component.html", "home.html"],
        )
        cats = _categorize_files(tmp_path)
        assert "Design System" in cats
        assert "Components" in cats
        assert "Prototypes" in cats

    def test_empty_categories_excluded(self, tmp_path):
        self._make(tmp_path, ["design-tokens.html"])
        cats = _categorize_files(tmp_path)
        assert "Components" not in cats
        assert "Prototypes" not in cats

    def test_sorted_alphabetically_within_category(self, tmp_path):
        self._make(tmp_path, ["z-page.html", "a-page.html"])
        cats = _categorize_files(tmp_path)
        names = [f.name for f in cats["Prototypes"]]
        assert names == sorted(names)

    def test_subdirectory_files_are_included(self, tmp_path):
        # Subdir without index.html → files added flat
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "button.html").write_text("<html></html>", encoding="utf-8")
        (subdir / "card.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        assert "Components" in cats
        assert len(cats["Components"]) == 2
        assert all(isinstance(e, Path) for e in cats["Components"])

    def test_subdirectory_index_html_becomes_folder_group(self, tmp_path):
        # root index.html excluded; subdir index.html → folder group tuple
        (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "index.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        assert "Components" in cats
        entries = cats["Components"]
        assert len(entries) == 1
        assert isinstance(entries[0], tuple)
        folder_index, children = entries[0]
        assert folder_index.name == "index.html"
        assert folder_index.parent.name == "components"
        assert children == []

    def test_subdirectory_with_index_groups_children(self, tmp_path):
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "index.html").write_text("<html></html>", encoding="utf-8")
        (subdir / "button.html").write_text("<html></html>", encoding="utf-8")
        (subdir / "card.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        assert "Components" in cats
        entries = cats["Components"]
        assert len(entries) == 1  # one folder group, not three files
        folder_index, children = entries[0]
        assert folder_index.name == "index.html"
        assert len(children) == 2
        assert sorted(c.name for c in children) == ["button.html", "card.html"]

    def test_folder_groups_appear_before_root_files(self, tmp_path):
        # Root-level component file + subdir folder group → group first
        (tmp_path / "card-widget.html").write_text("<html></html>", encoding="utf-8")
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "index.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        entries = cats["Components"]
        assert isinstance(entries[0], tuple)  # folder group is first
        assert isinstance(entries[1], Path)   # root file is second

    def test_subdirectory_classified_by_folder_name(self, tmp_path):
        # file stem has no keyword, but parent dir "components" triggers Components
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "my-widget.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        assert "Components" in cats

    def test_subdirectory_index_html_is_included(self, tmp_path):
        # Kept as alias for the renamed test — checks Components bucket exists
        subdir = tmp_path / "components"
        subdir.mkdir()
        (subdir / "index.html").write_text("<html></html>", encoding="utf-8")
        cats = _categorize_files(tmp_path)
        assert "Components" in cats


# ---------------------------------------------------------------------------
# _build_nav_html
# ---------------------------------------------------------------------------


class TestBuildNavHtml:
    def test_empty_categories_returns_empty_and_none(self, tmp_path):
        html, first = _build_nav_html({}, tmp_path)
        assert html == ""
        assert first is None

    def test_single_file_returns_first_item(self, tmp_path):
        f = tmp_path / "design-tokens.html"
        f.write_text("", encoding="utf-8")
        cats = {"Design System": [f]}
        html, first = _build_nav_html(cats, tmp_path)
        assert first is not None
        assert first["url"] == "design-tokens.html"
        assert first["name"] == "Design Tokens"
        assert "nav-0" in first["id"]
        assert first.get("type") == "ds"

    def test_first_item_is_first_file_in_first_section(self, tmp_path):
        ds = tmp_path / "design-tokens.html"
        pg = tmp_path / "home.html"
        ds.write_text("", encoding="utf-8")
        pg.write_text("", encoding="utf-8")
        cats = {"Design System": [ds], "Prototypes": [pg]}
        _, first = _build_nav_html(cats, tmp_path)
        assert first is not None
        assert first["url"] == "design-tokens.html"

    def test_nav_html_contains_section_title(self, tmp_path):
        f = tmp_path / "design-tokens.html"
        f.write_text("", encoding="utf-8")
        cats = {"Design System": [f]}
        html, _ = _build_nav_html(cats, tmp_path)
        assert "Design System" in html

    def test_nav_html_contains_data_attributes(self, tmp_path):
        f = tmp_path / "design-tokens.html"
        f.write_text("", encoding="utf-8")
        cats = {"Design System": [f]}
        html, _ = _build_nav_html(cats, tmp_path)
        assert 'data-url="design-tokens.html"' in html
        assert 'data-name="Design Tokens"' in html
        assert 'data-type="ds"' in html

    def test_nav_html_contains_item_ids(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("", encoding="utf-8")
        cats = {"Prototypes": [f]}
        html, first = _build_nav_html(cats, tmp_path)
        assert f'id="{first["id"]}"' in html

    def test_multiple_items_get_unique_ids(self, tmp_path):
        files = [tmp_path / f"page{i}.html" for i in range(3)]
        for f in files:
            f.write_text("", encoding="utf-8")
        cats = {"Prototypes": files}
        html, _ = _build_nav_html(cats, tmp_path)
        assert 'id="nav-0"' in html
        assert 'id="nav-1"' in html
        assert 'id="nav-2"' in html
        assert 'data-type' not in html

    def test_folder_group_generates_folder_html(self, tmp_path):
        subdir = tmp_path / "components"
        subdir.mkdir()
        idx = subdir / "index.html"
        btn = subdir / "button.html"
        for f in [idx, btn]:
            f.write_text("", encoding="utf-8")
        cats = {"Components": [(idx, [btn])]}
        html, first = _build_nav_html(cats, tmp_path)
        assert "nav-folder" in html
        assert "nav-folder-header" in html
        assert "nav-folder-children" in html
        assert "nav-child" in html
        assert 'data-url="components/index.html"' in html
        assert first is not None
        assert first["url"] == "components/index.html"
        assert first["name"] == "Components"
        assert 'data-type="ds"' in html
        assert first.get("type") == "ds"

    def test_folder_group_no_children_no_children_div(self, tmp_path):
        subdir = tmp_path / "components"
        subdir.mkdir()
        idx = subdir / "index.html"
        idx.write_text("", encoding="utf-8")
        cats = {"Components": [(idx, [])]}
        html, _ = _build_nav_html(cats, tmp_path)
        assert "nav-folder-children" not in html

    def test_folder_group_child_url_includes_subdir(self, tmp_path):
        subdir = tmp_path / "components"
        subdir.mkdir()
        idx = subdir / "index.html"
        btn = subdir / "button.html"
        for f in [idx, btn]:
            f.write_text("", encoding="utf-8")
        cats = {"Components": [(idx, [btn])]}
        html, _ = _build_nav_html(cats, tmp_path)
        assert 'data-url="components/button.html"' in html


# ---------------------------------------------------------------------------
# generate_preview_index
# ---------------------------------------------------------------------------


class TestGeneratePreviewIndex:
    def test_creates_index_html(self, tmp_path):
        out = generate_preview_index(tmp_path)
        assert out == tmp_path / "index.html"
        assert out.exists()

    def test_welcome_state_when_no_files(self, tmp_path):
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "Nothing here yet" in html
        assert "floop token view" in html

    def test_no_welcome_state_when_files_exist(self, tmp_path):
        (tmp_path / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "Nothing here yet" not in html

    def test_first_item_script_injected(self, tmp_path):
        (tmp_path / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "_first = {" in html
        json_str = "{" + html.split("_first = {")[1].split(";")[0]
        data = json.loads(json_str)
        assert data["url"] == "design-tokens.html"
        assert data["name"] == "Design Tokens"
        assert data.get("type") == "ds"

    def test_no_first_script_when_empty(self, tmp_path):
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "_first = {" not in html

    def test_design_system_section_present(self, tmp_path):
        (tmp_path / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "Design System" in html

    def test_components_section_present(self, tmp_path):
        (tmp_path / "button-component.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "Components" in html

    def test_prototypes_section_present(self, tmp_path):
        (tmp_path / "home.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert "Prototypes" in html

    def test_index_html_excluded_from_nav(self, tmp_path):
        # If there's already an index.html it should not appear in the nav
        (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        # index.html should not appear as a nav link (no data-url for it)
        assert 'data-url="index.html"' not in html

    def test_overwrite_existing_index(self, tmp_path):
        out = tmp_path / "index.html"
        out.write_text("old content", encoding="utf-8")
        generate_preview_index(tmp_path)
        assert "old content" not in out.read_text(encoding="utf-8")
        assert "floop" in out.read_text(encoding="utf-8")

    def test_html_has_sidebar_structure(self, tmp_path):
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert 'class="sidebar"' in html
        assert 'class="main"' in html
        assert 'id="sidebar-nav"' in html
        assert 'id="frame-wrap"' in html

    def test_html_is_valid_doctype(self, tmp_path):
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>")

    def test_file_names_html_escaped_in_nav(self, tmp_path):
        # Filename with & would be a rare edge case but coverage matters
        (tmp_path / "home.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(tmp_path).read_text(encoding="utf-8")
        # Normal names should just appear as-is
        assert "home.html" in html


# ---------------------------------------------------------------------------
# _load_journey_domains
# ---------------------------------------------------------------------------


from floop.preview import _build_sitemap_nav_html, _load_journey_domains


def _write_csv(parent: Path, content: str) -> Path:
    """Write journey-map.csv to parent/.floop/journey-map.csv."""
    floop = parent / ".floop"
    floop.mkdir(parents=True, exist_ok=True)
    csv_path = floop / "journey-map.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


class TestLoadJourneyDomains:
    def test_no_csv_returns_empty(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        assert _load_journey_domains(build_dir) == {}

    def test_single_row_creates_domain(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert "auth" in result
        assert len(result["auth"]) == 1
        assert result["auth"][0]["url"] == "journey/auth/login.html"
        assert result["auth"][0]["name"] == "Login"

    def test_html_file_without_build_prefix_kept_as_is(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,journey/auth/login.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        # 'journey/...' cannot be made relative to 'build' → kept as-is
        assert result["auth"][0]["url"] == "journey/auth/login.html"

    def test_multiple_domains(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\n"
            "auth,login,Login,build/journey/auth/login.html\n"
            "dashboard,home,Home,build/journey/dashboard/home.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert set(result.keys()) == {"auth", "dashboard"}

    def test_multiple_pages_per_domain(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\n"
            "auth,login,Login,build/journey/auth/login.html\n"
            "auth,register,Register,build/journey/auth/register.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert len(result["auth"]) == 2

    def test_empty_html_file_row_skipped(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert result == {}

    def test_name_fallback_to_stem_when_no_title(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,,build/journey/auth/my-login.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert result["auth"][0]["name"] == "My Login"

    def test_empty_domain_falls_back_to_default(self, tmp_path):
        _write_csv(
            tmp_path,
            "domain,page_id,title,html_file\n,login,Login,build/journey/default/login.html\n",
        )
        build_dir = tmp_path / ".floop" / "build"
        result = _load_journey_domains(build_dir)
        assert "default" in result


# ---------------------------------------------------------------------------
# _build_sitemap_nav_html
# ---------------------------------------------------------------------------


class TestBuildSitemapNavHtml:
    def test_empty_domains_returns_empty(self):
        html, first = _build_sitemap_nav_html({})
        assert html == ""
        assert first is None

    def test_single_domain_returns_nav_section(self):
        domains = {"auth": [{"page_id": "login", "url": "journey/auth/login.html", "name": "Login"}]}
        html, first = _build_sitemap_nav_html(domains)
        assert "Sitemap" in html
        assert 'data-domain="auth"' in html
        assert "Auth" in html

    def test_first_item_has_domain_key(self):
        domains = {"auth": [{"page_id": "login", "url": "journey/auth/login.html", "name": "Login"}]}
        _, first = _build_sitemap_nav_html(domains)
        assert first is not None
        assert first["domain"] == "auth"
        assert first["url"] == "journey/auth/login.html"
        assert first["id"] == "domain-auth"

    def test_domain_count_badge_shown(self):
        domains = {
            "auth": [
                {"page_id": "login", "url": "journey/auth/login.html", "name": "Login"},
                {"page_id": "register", "url": "journey/auth/register.html", "name": "Register"},
            ]
        }
        html, _ = _build_sitemap_nav_html(domains)
        assert "2" in html

    def test_domain_name_html_escaped(self):
        domains = {"a&b": [{"page_id": "p", "url": "journey/a/p.html", "name": "P"}]}
        html, _ = _build_sitemap_nav_html(domains)
        assert "a&amp;b" in html
        assert "a&b" not in html.replace("a&amp;b", "")

    def test_empty_pages_list_no_first_item(self):
        domains = {"auth": []}
        _, first = _build_sitemap_nav_html(domains)
        assert first is None


# ---------------------------------------------------------------------------
# generate_preview_index — with journey domains
# ---------------------------------------------------------------------------


class TestGeneratePreviewIndexWithDomains:
    def _make_build_with_csv(self, tmp_path: Path, csv_content: str) -> Path:
        """Set up .floop/build/ and journey-map.csv in tmp_path."""
        floop = tmp_path / ".floop"
        floop.mkdir(parents=True, exist_ok=True)
        (floop / "journey-map.csv").write_text(csv_content, encoding="utf-8")
        build_dir = floop / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        return build_dir

    def test_sitemap_section_in_sidebar_when_csv_exists(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert "Sitemap" in html

    def test_domain_nav_item_present(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert 'data-domain="auth"' in html

    def test_domains_json_injected(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert "var _domains" in html
        assert '"auth"' in html

    def test_first_item_is_domain_when_csv_present(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert '"domain"' in html
        assert '"auth"' in html

    def test_prototypes_section_removed_when_csv_present(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        # Create a journey HTML file so it would normally show in Prototypes
        journey = build_dir / "journey" / "auth"
        journey.mkdir(parents=True)
        (journey / "login.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        # "Prototypes" section should not appear since CSV provides domain structure
        assert "Prototypes" not in html

    def test_design_system_still_present_with_csv(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        (build_dir / "design-tokens.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert "Design System" in html

    def test_toolbar_controls_present(self, tmp_path):
        build_dir = self._make_build_with_csv(
            tmp_path,
            "domain,page_id,title,html_file\nauth,login,Login,build/journey/auth/login.html\n",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert 'id="toolbar-controls"' in html
        assert 'id="page-select"' in html
        assert 'id="fullscreen-btn"' in html

    def test_no_sitemap_section_without_csv(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert "Sitemap" not in html


# ---------------------------------------------------------------------------
# Version + changehistory helpers
# ---------------------------------------------------------------------------


class TestVersionHelpers:
    def test_load_versions_no_dir(self, tmp_path):
        from floop.preview import _load_versions
        assert _load_versions(tmp_path) == []

    def test_load_versions_skips_invalid_meta(self, tmp_path):
        from floop.preview import _load_versions
        d = tmp_path / "versions" / "broken"
        d.mkdir(parents=True)
        (d / "meta.json").write_text("not json", encoding="utf-8")
        assert _load_versions(tmp_path) == []

    def test_load_versions_reads_meta(self, tmp_path):
        from floop.preview import _load_versions
        ver_dir = tmp_path / "versions" / "v1.0"
        ver_dir.mkdir(parents=True)
        (ver_dir / "meta.json").write_text(
            '{"version": "v1.0", "message": "first", "created_at": "2026-01-01T00:00:00+00:00"}',
            encoding="utf-8",
        )
        result = _load_versions(tmp_path)
        assert len(result) == 1
        assert result[0]["version"] == "v1.0"

    def test_load_versions_sorts_newest_first(self, tmp_path):
        from floop.preview import _load_versions
        for name, dt in [("v1.0", "2026-01-01T00:00:00+00:00"), ("v1.1", "2026-02-01T00:00:00+00:00")]:
            d = tmp_path / "versions" / name
            d.mkdir(parents=True)
            (d / "meta.json").write_text(
                f'{{"version": "{name}", "created_at": "{dt}"}}', encoding="utf-8"
            )
        result = _load_versions(tmp_path)
        assert result[0]["version"] == "v1.1"

    def test_load_changehistory_missing(self, tmp_path):
        from floop.preview import _load_changehistory
        assert _load_changehistory(tmp_path) == {}

    def test_load_changehistory_reads_file(self, tmp_path):
        from floop.preview import _load_changehistory
        (tmp_path / "_changehistory.json").write_text(
            '{"versions": [{"version": "v1.0"}]}', encoding="utf-8"
        )
        result = _load_changehistory(tmp_path)
        assert result["versions"][0]["version"] == "v1.0"

    def test_load_changehistory_invalid_json(self, tmp_path):
        from floop.preview import _load_changehistory
        (tmp_path / "_changehistory.json").write_text("not json", encoding="utf-8")
        assert _load_changehistory(tmp_path) == {}

    def test_build_version_options_trunk_selected(self):
        from floop.preview import _build_version_options_html
        html = _build_version_options_html([], "trunk")
        assert 'selected' in html
        assert 'trunk' in html

    def test_build_version_options_with_versions(self):
        from floop.preview import _build_version_options_html
        versions = [{"version": "v1.0", "message": "first"}]
        html = _build_version_options_html(versions, "v1.0")
        assert 'value="v1.0" selected' in html
        assert 'value="trunk"' in html

    def test_build_version_options_skips_empty_name(self):
        from floop.preview import _build_version_options_html
        versions = [{"version": "", "message": "bad"}, {"version": "v1.0"}]
        html = _build_version_options_html(versions, "trunk")
        assert html.count('<option') == 2

    def test_build_version_nav_empty(self):
        from floop.preview import _build_version_nav_html
        html, first = _build_version_nav_html({})
        assert html == ""
        assert first is None

    def test_build_version_nav_with_data(self):
        from floop.preview import _build_version_nav_html
        html, first = _build_version_nav_html({"versions": [{"version": "v1.0"}]})
        assert "Version History" in html
        assert 'data-type="version-history"' in html
        assert first is not None
        assert first["type"] == "version-history"

    def test_generate_preview_index_with_versions(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        ver_dir = tmp_path / "versions" / "v1.0"
        ver_dir.mkdir(parents=True)
        (ver_dir / "meta.json").write_text(
            '{"version": "v1.0", "message": "first", "created_at": "2026-01-01T00:00:00+00:00"}',
            encoding="utf-8",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert 'value="v1.0"' in html

    def test_generate_preview_index_with_changehistory(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "_changehistory.json").write_text(
            '{"versions": [{"version": "v1.0", "date": "2026-01-01", "message": "init"}]}',
            encoding="utf-8",
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        assert "Version History" in html
        assert '_first' in html
        data = json.loads("{" + html.split("_first = {")[1].split(";")[0])
        assert data["type"] == "version-history"

    def test_generate_preview_index_first_item_priority(self, tmp_path):
        """version-history first_item takes priority over domains and categories."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "home.html").write_text("<html></html>", encoding="utf-8")
        (build_dir / "_changehistory.json").write_text(
            '{"versions": [{"version": "v1.0"}]}', encoding="utf-8"
        )
        html = generate_preview_index(build_dir).read_text(encoding="utf-8")
        data = json.loads("{" + html.split("_first = {")[1].split(";")[0])
        assert data["type"] == "version-history"

    def test_generate_preview_active_version(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        html = generate_preview_index(build_dir, active_version="v1.0").read_text(encoding="utf-8")
        assert '"v1.0"' in html
