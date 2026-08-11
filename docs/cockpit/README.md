# EvoGen evidence cockpit

Open `index.html` directly in a browser. It has no network, package, font, or
server dependency and works through `file://`.

The interface is a derived evidence view. Its authorities are
`../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md`, `../INTEGRATION_CHECKPOINT.md`, and
the reviewed narrative in `content.json`. The builder refuses disagreement
about the 49-goal registry, the sole next goal, the latest closed goal, and the
KAE evidence commit.

Rebuild after changing any authority:

```bash
python scripts/build_project_cockpit.py
```

Verify freshness without writing:

```bash
python scripts/build_project_cockpit.py --check
```

`state.json`, `state.js`, and the no-JavaScript summary in `index.html` are
generated. `state.js` is deliberately a classic global script so the complete
interface works when opened directly instead of relying on `fetch()` or module
loading under `file://`.
