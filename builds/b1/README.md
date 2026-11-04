# Build 1: Agent Traffic Dashboard

First build of `SPEC.md`. Python 3.8+ standard library only, nothing to install.

```bash
# from the repo root, three terminals:
python3 proxy.py --port 8041                                                # 1. the given proxy
python3 builds/b1/dashboard.py --port 8042 --upstream http://localhost:8041  # 2. the dashboard
ANTHROPIC_BASE_URL=http://localhost:8042 claude                             # 3. the agent
# open http://localhost:8042/dashboard
```

Files:
- `dashboard.py`: pass-through proxy + SSE event stream + reply reassembly + price table.
- `dashboard.html`: the page (inline CSS and JS, no external resources).
- `ASSUMPTIONS.md`: every choice the spec did not settle, and questions for the next spec version.
