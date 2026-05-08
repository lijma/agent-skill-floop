# Command Reference

### Project

```bash
floop init                    # Create .floop/ directory structure
floop enable <agent>          # Install skills into AI agent
```

### Design Tokens

```bash
floop token init              # Generate global/semantic/component.tokens.json templates
floop token validate          # Validate W3C DTCG format + cross-references
floop token view              # Generate design-tokens.html + tokens.css
```

### Prototype Artifacts

```bash
floop prd init/validate            # .floop/prd.md — Product Requirements Document
floop sitemap init/validate        # .floop/sitemap.md — Page structure
floop prototype init               # Generate journey-map.csv from sitemap.md
floop prototype validate           # Check HTML files mapped + domains in sitemap
floop component init/validate      # .floop/components.yaml — Component library
```

### Quality

```bash
floop journey check <file>    # Backward-check a journey HTML:
                              #   • head links (tokens.css, components.js)
                              #   • token references (var(--x) → *.tokens.json)
                              #   • component coverage (unused components)
                              #   • raw tag detection (bare <button> without component wiring)
```

### Versions

```bash
floop version create <name>   # Snapshot build/ → .floop/versions/<name>/
floop version list            # List all saved versions
```

### Review

```bash
floop review set                                  # Step 1: configure server/API key/project key
floop review --version <name>                         # Upload a saved version to floop-server
floop review --server-url <url> --project-key <key>   # Configure SaaS/self-host target
floop review --project-key <key> --api-key flp_...    # CLI values are saved to .floop/floop.env
```

Use review in two steps:

1. `floop review set` creates or updates `.floop/floop.env`, validates the API key by listing projects, and writes `FLOOP_PROJECT_KEY` by selecting or creating a project.
2. `floop review --version <name>` checks the saved version/build and uploads it.

`floop review` reads `.floop/floop.env` first. If required values are missing, it creates or updates this template and asks you to run `floop review set`:

```env
FLOOP_SERVER_URL=https://floop-server.vercel.app
FLOOP_PROJECT_KEY=proj_...
FLOOP_API_KEY=flp_...
```

Missing setup exits successfully with `status: setup_required` in JSON mode so Agents can read the next action. Treat it as incomplete setup, not a successful upload; a real upload result includes `shareUrl`.

The file is added to `.floop/.gitignore` because it stores the API key.

`floop preview` renders its navigation shell at runtime and does not write
`.floop/build/index.html`, so `floop review` uploads only real build artifacts.

### Preview

```bash
floop preview                         # Serve .floop/ locally (trunk)
floop preview --version <name>        # Serve a named version snapshot
floop preview --port 8080             # Custom port
```
