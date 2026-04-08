"""Tests for floop.adapters — Agent platform adapters."""

from pathlib import Path

import pytest

from floop.adapters import (
    ADAPTERS,
    SUPPORTED_AGENTS,
    ClaudeAdapter,
    CopilotAdapter,
    CursorAdapter,
    OpenClawAdapter,
    OpenCodeAdapter,
    QwenCodeAdapter,
    TraeAdapter,
)
from floop.skills import SKILLS


class TestAdapterRegistry:
    def test_all_agents_registered(self):
        assert set(SUPPORTED_AGENTS) == {
            "copilot", "cursor", "claude",
            "trae", "qwen-code", "opencode", "openclaw",
        }

    def test_registry_matches_supported(self):
        assert set(ADAPTERS.keys()) == set(SUPPORTED_AGENTS)


class TestCopilotAdapter:
    def test_install_creates_skill_dirs(self, tmp_path):
        adapter = CopilotAdapter()
        created = adapter.install(tmp_path)
        skill_files = [p for p in created if p.name == "SKILL.md"]
        assert len(skill_files) == len(SKILLS)
        for path in skill_files:
            assert path.exists()

    def test_install_creates_instruction(self, tmp_path):
        adapter = CopilotAdapter()
        adapter.install(tmp_path)
        instr = tmp_path / ".github" / "instructions" / "floop.instructions.md"
        assert instr.exists()
        content = instr.read_text(encoding="utf-8")
        assert "applyTo: '**'" in content
        assert "floop" in content
        assert "floop token" in content

    def test_skill_has_frontmatter(self, tmp_path):
        adapter = CopilotAdapter()
        adapter.install(tmp_path)
        for skill in SKILLS.values():
            path = tmp_path / ".github" / "skills" / skill["name"] / "SKILL.md"
            content = path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert f'name: {skill["name"]}' in content

    def test_skills_reference_json_not_yaml(self, tmp_path):
        adapter = CopilotAdapter()
        adapter.install(tmp_path)
        for skill in SKILLS.values():
            path = tmp_path / ".github" / "skills" / skill["name"] / "SKILL.md"
            content = path.read_text(encoding="utf-8")
            # prototype and design-system skills should reference JSON, not YAML
            if skill["name"] in ("floop-prototype", "floop-design-system"):
                assert "tokens.json" in content or "DTCG" in content


class TestCursorAdapter:
    def test_install_creates_mdc_files(self, tmp_path):
        adapter = CursorAdapter()
        created = adapter.install(tmp_path)
        skill_files = [p for p in created if p.name != "floop.mdc"]
        assert len(skill_files) == len(SKILLS)
        for path in skill_files:
            assert path.exists()
            assert path.suffix == ".mdc"

    def test_install_creates_always_on_rule(self, tmp_path):
        adapter = CursorAdapter()
        adapter.install(tmp_path)
        instr = tmp_path / ".cursor" / "rules" / "floop.mdc"
        assert instr.exists()
        content = instr.read_text(encoding="utf-8")
        assert "alwaysApply: true" in content
        assert "floop" in content

    def test_mdc_has_frontmatter(self, tmp_path):
        adapter = CursorAdapter()
        adapter.install(tmp_path)
        rules_dir = tmp_path / ".cursor" / "rules"
        for f in rules_dir.glob("*.mdc"):
            content = f.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert "description:" in content


class TestClaudeAdapter:
    def test_install_creates_skill_dirs(self, tmp_path):
        adapter = ClaudeAdapter()
        created = adapter.install(tmp_path)
        # Skills + CLAUDE.md
        skill_files = [p for p in created if p.name == "SKILL.md"]
        assert len(skill_files) == len(SKILLS)

    def test_creates_claude_md(self, tmp_path):
        adapter = ClaudeAdapter()
        adapter.install(tmp_path)
        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text(encoding="utf-8")
        assert "floop:skills" in content
        assert "floop Skills" in content

    def test_claude_md_update_idempotent(self, tmp_path):
        adapter = ClaudeAdapter()
        adapter.install(tmp_path)
        first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        adapter.install(tmp_path)
        second = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        # Should replace, not duplicate
        assert second.count("floop:skills") == 2  # open + close markers

    def test_claude_md_appends_to_existing(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Existing content\n\nHello world\n", encoding="utf-8")
        adapter = ClaudeAdapter()
        adapter.install(tmp_path)
        content = claude_md.read_text(encoding="utf-8")
        assert "Existing content" in content
        assert "floop:skills" in content

    def test_claude_md_missing_end_marker(self, tmp_path):
        """CLAUDE.md has open marker but no close marker."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "# Pre\n<!-- floop:skills -->\nold stuff\n", encoding="utf-8"
        )
        adapter = ClaudeAdapter()
        adapter.install(tmp_path)
        content = claude_md.read_text(encoding="utf-8")
        assert "# Pre" in content
        assert "old stuff" not in content  # replaced
        assert "floop Skills" in content


class TestTraeAdapter:
    def test_install_creates_project_rules(self, tmp_path):
        adapter = TraeAdapter()
        created = adapter.install(tmp_path)
        assert len(created) == 1
        path = tmp_path / ".trae" / "project_rules.md"
        assert path.exists()
        assert path in created

    def test_rules_contains_instruction(self, tmp_path):
        adapter = TraeAdapter()
        adapter.install(tmp_path)
        content = (tmp_path / ".trae" / "project_rules.md").read_text(encoding="utf-8")
        assert "floop" in content
        assert "floop token" in content

    def test_rules_contains_all_skills(self, tmp_path):
        adapter = TraeAdapter()
        adapter.install(tmp_path)
        content = (tmp_path / ".trae" / "project_rules.md").read_text(encoding="utf-8")
        for skill in SKILLS.values():
            assert skill["name"] in content

    def test_install_idempotent(self, tmp_path):
        adapter = TraeAdapter()
        adapter.install(tmp_path)
        first = (tmp_path / ".trae" / "project_rules.md").read_text(encoding="utf-8")
        adapter.install(tmp_path)
        second = (tmp_path / ".trae" / "project_rules.md").read_text(encoding="utf-8")
        assert first == second


class TestQwenCodeAdapter:
    def test_install_creates_agents_md(self, tmp_path):
        adapter = QwenCodeAdapter()
        created = adapter.install(tmp_path)
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        assert agents_md in created

    def test_no_skills_dir_created(self, tmp_path):
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        assert not (tmp_path / ".qwen-code").exists()

    def test_agents_md_contains_instruction(self, tmp_path):
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "floop:skills" in content
        assert "floop token" in content

    def test_agents_md_idempotent(self, tmp_path):
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        # Section replaced, not duplicated
        assert content.count("floop:skills") == 2  # open + close markers

    def test_agents_md_appends_to_existing(self, tmp_path):
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text("# Existing\n\nHello\n", encoding="utf-8")
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        content = agents_md.read_text(encoding="utf-8")
        assert "Existing" in content
        assert "floop:skills" in content

    def test_agents_md_replaces_existing_section(self, tmp_path):
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text(
            "# Pre\n<!-- floop:skills -->\nold stuff\n<!-- /floop:skills -->\n",
            encoding="utf-8",
        )
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        content = agents_md.read_text(encoding="utf-8")
        assert "# Pre" in content
        assert "old stuff" not in content
        assert "floop" in content

    def test_agents_md_missing_end_marker(self, tmp_path):
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text(
            "# Pre\n<!-- floop:skills -->\nold stuff\n", encoding="utf-8"
        )
        adapter = QwenCodeAdapter()
        adapter.install(tmp_path)
        content = agents_md.read_text(encoding="utf-8")
        assert "old stuff" not in content
        assert "floop" in content


class TestOpenCodeAdapter:
    def test_install_creates_skill_files(self, tmp_path):
        adapter = OpenCodeAdapter()
        created = adapter.install(tmp_path)
        skill_files = [p for p in created if p.name == "SKILL.md"]
        assert len(skill_files) == len(SKILLS)
        for f in skill_files:
            assert f.exists()
            assert ".opencode" in str(f)

    def test_install_creates_agents_md(self, tmp_path):
        adapter = OpenCodeAdapter()
        adapter.install(tmp_path)
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text(encoding="utf-8")
        assert "floop:skills" in content

    def test_skill_has_frontmatter(self, tmp_path):
        adapter = OpenCodeAdapter()
        adapter.install(tmp_path)
        for skill in SKILLS.values():
            path = tmp_path / ".opencode" / "skills" / skill["name"] / "SKILL.md"
            content = path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert f'name: {skill["name"]}' in content

    def test_agents_md_references_skill_files(self, tmp_path):
        adapter = OpenCodeAdapter()
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert ".opencode/skills/" in content

    def test_agents_md_idempotent(self, tmp_path):
        adapter = OpenCodeAdapter()
        adapter.install(tmp_path)
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert content.count("floop:skills") == 2


class TestOpenClawAdapter:
    def test_install_creates_skill_files(self, tmp_path):
        adapter = OpenClawAdapter()
        created = adapter.install(tmp_path)
        skill_files = [p for p in created if p.name == "SKILL.md"]
        assert len(skill_files) == len(SKILLS)
        for f in skill_files:
            assert f.exists()
            assert ".openclaw" in str(f)

    def test_install_creates_agents_md(self, tmp_path):
        adapter = OpenClawAdapter()
        adapter.install(tmp_path)
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text(encoding="utf-8")
        assert "floop:skills" in content

    def test_skill_has_frontmatter(self, tmp_path):
        adapter = OpenClawAdapter()
        adapter.install(tmp_path)
        for skill in SKILLS.values():
            path = tmp_path / ".openclaw" / "skills" / skill["name"] / "SKILL.md"
            content = path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert f'name: {skill["name"]}' in content

    def test_agents_md_references_skill_files(self, tmp_path):
        adapter = OpenClawAdapter()
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert ".openclaw/skills/" in content

    def test_agents_md_idempotent(self, tmp_path):
        adapter = OpenClawAdapter()
        adapter.install(tmp_path)
        adapter.install(tmp_path)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert content.count("floop:skills") == 2
