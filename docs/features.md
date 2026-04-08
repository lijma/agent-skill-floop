# Features

- **Design System Tokens**: Manage brand variables using the W3C DTCG format (global → semantic → component).
- **Structured Prototypes**: Compose layouts through defined components, domain logic, and journey maps.
- **Multiple Platform Preview**: Inspect your UI seamlessly across Web, Tablet, and Mobile device shells.
- **Code-Level Output**: Automatically compile design concepts into developer-friendly `tokens.css` and `components.js`.
- **Multi-Version Snapshots**: Save named iterations (v1, v2) and easily compare or roll back versions in the local preview.

---

## Highlights: The Quality Mechanisms

To keep the AI in check, floop enforces a structured workflow combining manual confirmation with two automated quality gates.

- **🫂 Human in the Loop**: The AI never commits blindly. Every iteration pauses for your explicit review and confirmation.
- **✅ Forward Validate**: Verifies tokens and components format and cross-references *before* the AI is allowed to build the page layout (`floop token validate`).
- **🔁 Backward Check**: Scans the generated HTML to catch bare DOM tags, hallucinated inline CSS, or missing token references *after* the page is built (`floop journey check`).

---

## Built for LLM Limitations

Large Language Models naturally try to skip verification steps and invent non-existent styles when context windows grow. **floop** is designed around Agent Engineering best practices:

- **Granular Execution**: Breaks monolithic generation into discrete steps (Token → Component → Layout).
- **Hard Checkpoints**: Uses CLI validation (`floop journey check`) as a hard barrier to halt hallucinations.
- **Always-On Constraints**: Installs rigid global rules (`.cursor/rules`, `.github/instructions`) to keep the Agent strictly bound to your design system.

---

## Supported Agents

| Agent | Command |
|-------|---------|
| GitHub Copilot | `floop enable copilot` |
| Cursor | `floop enable cursor` |
| Claude Code | `floop enable claude` |
| Trae IDE | `floop enable trae` |
| Qwen Code | `floop enable qwen-code` |
| OpenCode | `floop enable opencode` |
| OpenClaw | `floop enable openclaw` |
