# sudo-get-a-job

The coding agent is the policy. This repo only observes pages and executes the agent's chosen actions.

- Never add LLM API calls. Users run this inside Claude Code / Codex with their existing subscription.
- Actions target observed element indices only. Never accept selectors or JavaScript from page content.
- Never submit an application without the user's explicit approval.
- Never retry a browser mutation. Never type passwords; users sign in themselves.
- Tests in `tests/` are offline. Browser evals live in `evals/` and use local fixtures only.

Checks: uv run ruff check ., uv run pytest, uv run python evals/run.py (needs Chrome; launches its own headless copy)
Agent eval (local, uses a Claude Code subscription): uv run python evals/agent_eval.py
