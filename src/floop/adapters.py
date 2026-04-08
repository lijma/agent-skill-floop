"""Agent platform adapters for floop skill installation.

Each adapter knows how to write floop skills into the target agent's
configuration format and directory structure.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import click

from floop.skills import INSTRUCTION, SKILLS


class AgentAdapter(Protocol):
    """Interface for agent platform adapters."""

    name: str

    def install(self, project_dir: Path) -> list[Path]:
        """Install all floop skills into the project. Returns created file paths."""
        ...


# ---------------------------------------------------------------------------
# Copilot (VS Code / GitHub Copilot)
# Format: .github/skills/<name>/SKILL.md with YAML frontmatter
# ---------------------------------------------------------------------------

class CopilotAdapter:
    name = "copilot"

    def install(self, project_dir: Path) -> list[Path]:
        created: list[Path] = []

        # Write instruction file (always-on context)
        instr_dir = project_dir / ".github" / "instructions"
        instr_dir.mkdir(parents=True, exist_ok=True)
        instr_path = instr_dir / "floop.instructions.md"
        instr_path.write_text(
            "---\n"
            "description: 'This project uses floop for prototype development. "
            "Follow the floop workflow for design tokens, sitemap, components, and page generation.'\n"
            "applyTo: '**'\n"
            "---\n\n"
            + INSTRUCTION,
            encoding="utf-8",
        )
        created.append(instr_path)

        # Write skill files
        skills_dir = project_dir / ".github" / "skills"

        for skill in SKILLS.values():
            skill_dir = skills_dir / skill["name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            path = skill_dir / "SKILL.md"
            path.write_text(self._render(skill), encoding="utf-8")
            created.append(path)

        return created

    @staticmethod
    def _render(skill: dict) -> str:
        return (
            f'---\n'
            f'name: {skill["name"]}\n'
            f'description: "{skill["description"]}"\n'
            f'---\n\n'
            f'{skill["content"]}'
        )


# ---------------------------------------------------------------------------
# Cursor
# Format: .cursor/rules/<name>.mdc with frontmatter
# ---------------------------------------------------------------------------

class CursorAdapter:
    name = "cursor"

    def install(self, project_dir: Path) -> list[Path]:
        created: list[Path] = []
        rules_dir = project_dir / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Write always-on instruction rule
        instr_path = rules_dir / "floop.mdc"
        instr_path.write_text(
            '---\n'
            'description: "floop prototype workflow — always-on context"\n'
            'globs: \n'
            'alwaysApply: true\n'
            '---\n\n'
            + INSTRUCTION,
            encoding="utf-8",
        )
        created.append(instr_path)

        # Write skill rules

        for skill in SKILLS.values():
            path = rules_dir / f'{skill["name"]}.mdc'
            path.write_text(self._render(skill), encoding="utf-8")
            created.append(path)

        return created

    @staticmethod
    def _render(skill: dict) -> str:
        return (
            f'---\n'
            f'description: "{skill["description"]}"\n'
            f'globs: \n'
            f'alwaysApply: false\n'
            f'---\n\n'
            f'{skill["content"]}'
        )


# ---------------------------------------------------------------------------
# Claude (Claude Code / Claude Desktop)
# Format: .claude/skills/<name>/SKILL.md  (same as Copilot structure)
#         or appended to CLAUDE.md
# ---------------------------------------------------------------------------

class ClaudeAdapter:
    name = "claude"

    def install(self, project_dir: Path) -> list[Path]:
        created: list[Path] = []

        # Write individual skill files
        skills_dir = project_dir / ".claude" / "skills"
        for skill in SKILLS.values():
            skill_dir = skills_dir / skill["name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            path = skill_dir / "SKILL.md"
            path.write_text(self._render(skill), encoding="utf-8")
            created.append(path)

        # Also append summary to CLAUDE.md for discovery
        claude_md = project_dir / "CLAUDE.md"
        marker = "<!-- floop:skills -->"
        section = self._render_claude_md()

        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            if marker in content:
                # Replace existing floop section
                before = content[: content.index(marker)]
                end_marker = "<!-- /floop:skills -->"
                if end_marker in content:
                    after = content[content.index(end_marker) + len(end_marker) :]
                else:
                    after = ""
                content = before + section + after
            else:
                content = content.rstrip() + "\n\n" + section
        else:
            content = section

        claude_md.write_text(content, encoding="utf-8")
        created.append(claude_md)

        return created

    @staticmethod
    def _render(skill: dict) -> str:
        return (
            f'---\n'
            f'name: {skill["name"]}\n'
            f'description: "{skill["description"]}"\n'
            f'---\n\n'
            f'{skill["content"]}'
        )

    @staticmethod
    def _render_claude_md() -> str:
        lines = ["<!-- floop:skills -->", "## floop Skills\n"]
        for skill in SKILLS.values():
            lines.append(f'- **{skill["name"]}**: {skill["description"]}')
            lines.append(
                f'  - See `.claude/skills/{skill["name"]}/SKILL.md` for full rules'
            )
        lines.append("\n<!-- /floop:skills -->")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Trae IDE
# Format: .trae/project_rules.md — single plain-Markdown rules file
# ---------------------------------------------------------------------------

class TraeAdapter:
    name = "trae"

    def install(self, project_dir: Path) -> list[Path]:
        rules_dir = project_dir / ".trae"
        rules_dir.mkdir(parents=True, exist_ok=True)
        path = rules_dir / "project_rules.md"
        path.write_text(self._render(), encoding="utf-8")
        return [path]

    @staticmethod
    def _render() -> str:
        lines = ["# floop Workflow Rules\n", INSTRUCTION, "\n## floop Skills\n"]
        for skill in SKILLS.values():
            lines.append(f'### {skill["name"]}\n')
            lines.append(skill["content"])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# AGENTS.md-based adapters (Qwen Code, OpenCode, OpenClaw)
# All write to AGENTS.md using <!-- floop:skills --> markers.
# OpenCode and OpenClaw also write per-skill files under .<agent>/skills/.
# ---------------------------------------------------------------------------

class _AgentsMdAdapter:
    """Base adapter for agents that read AGENTS.md at the project root."""

    name: str
    _skills_subdir: str | None = None  # e.g. "opencode" → .opencode/skills/

    def install(self, project_dir: Path) -> list[Path]:
        created: list[Path] = []

        if self._skills_subdir:
            skills_dir = project_dir / f".{self._skills_subdir}" / "skills"
            for skill in SKILLS.values():
                skill_dir = skills_dir / skill["name"]
                skill_dir.mkdir(parents=True, exist_ok=True)
                path = skill_dir / "SKILL.md"
                path.write_text(self._render_skill(skill), encoding="utf-8")
                created.append(path)

        agents_md = project_dir / "AGENTS.md"
        marker = "<!-- floop:skills -->"
        section = self._render_agents_md()

        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8")
            if marker in content:
                before = content[: content.index(marker)]
                end_marker = "<!-- /floop:skills -->"
                if end_marker in content:
                    after = content[content.index(end_marker) + len(end_marker):]
                else:
                    after = ""
                content = before + section + after
            else:
                content = content.rstrip() + "\n\n" + section
        else:
            content = section

        agents_md.write_text(content, encoding="utf-8")
        created.append(agents_md)
        return created

    @staticmethod
    def _render_skill(skill: dict) -> str:
        return (
            f'---\n'
            f'name: {skill["name"]}\n'
            f'description: "{skill["description"]}"\n'
            f'---\n\n'
            f'{skill["content"]}'
        )

    def _render_agents_md(self) -> str:
        lines = ["<!-- floop:skills -->", "## floop\n", INSTRUCTION]
        if self._skills_subdir:
            lines += ["", "## floop Skills\n"]
            for skill in SKILLS.values():
                lines.append(f'- **{skill["name"]}**: {skill["description"]}')
                lines.append(
                    f'  - See `.{self._skills_subdir}/skills/'
                    f'{skill["name"]}/SKILL.md` for full workflow'
                )
        lines.append("\n<!-- /floop:skills -->")
        return "\n".join(lines) + "\n"


class QwenCodeAdapter(_AgentsMdAdapter):
    """Qwen Code (terminal CLI, Gemini CLI fork) — AGENTS.md only."""
    name = "qwen-code"
    _skills_subdir = None


class OpenCodeAdapter(_AgentsMdAdapter):
    """OpenCode (terminal CLI) — AGENTS.md + .opencode/skills/."""
    name = "opencode"
    _skills_subdir = "opencode"


class OpenClawAdapter(_AgentsMdAdapter):
    """OpenClaw — AGENTS.md + .openclaw/skills/."""
    name = "openclaw"
    _skills_subdir = "openclaw"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ADAPTERS: dict[str, type[AgentAdapter]] = {
    "copilot": CopilotAdapter,
    "cursor": CursorAdapter,
    "claude": ClaudeAdapter,
    "trae": TraeAdapter,
    "qwen-code": QwenCodeAdapter,
    "opencode": OpenCodeAdapter,
    "openclaw": OpenClawAdapter,
}

SUPPORTED_AGENTS = list(ADAPTERS.keys())
