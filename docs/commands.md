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

### Preview

```bash
floop preview                         # Serve .floop/ locally (trunk)
floop preview --version <name>        # Serve a named version snapshot
floop preview --port 8080             # Custom port
```
