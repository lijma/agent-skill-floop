# Contributing

Because floop is fundamentally a tool focused on **Agent Engineering**, we welcome contributors looking to expand the toolkit of supported Agents or harden the validation mechanics of the CLI! 

## Getting Started

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/floop.git
cd floop/floop-cli

# 2. Install inside a virtual environment for development
pip install -e ".[test]"

# 3. Run the test suite (floop maintains 100% coverage)
pytest tests/

# 4. Want to add a new AI Agent to `floop enable`?
# Add yours directly in: src/floop/skills.py
```
