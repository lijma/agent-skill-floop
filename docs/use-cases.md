# Use Cases

floop guarantees consistency and reusability when relying on AI to prototype. Here are the core scenarios where the automated floop workflow ensures your project thrives rather than degrades.

### Scenario 1: The Global Redesign
**Problem:** "Make all the primary buttons slightly rounder, and change the brand color to purple." The AI updates the homepage perfectly, but forgets the dashboard, settings, and login pages.

**floop Solution:** The AI is instructed to update the `global.tokens.json`. You run `floop build`. Every single page across the entire project updates instantly with mathematical consistency. No manual sweeping required.

### Scenario 2: The Multi-Page Hallucination
**Problem:** When you ask the AI to build a list view for page 2, it invents a totally new card style with hardcoded `border-radius: 8px` and `#333` hex colors.

**floop Solution:** The AI is strictly bound by `.floop/components.yaml`. When it attempts to build page 2, `floop journey check` detects the bare `<div>` tags and inline styles. The check fails, and the agent is forced to rewrite the page using the registered `DataCard` component or fail the build.

### Scenario 3: Handoff to Engineering
**Problem:** Developers refuse to touch AI prototypes because they're a tangled mess of arbitrary class names and unmaintainable inline styles.

**floop Solution:** Because floop enforced standard `tokens.css` and documented `components.js` from day one, engineers can drop these exact artifacts directly into their React/Vue/Tailwind design systems. It's production-ready CSS architecture from the start.