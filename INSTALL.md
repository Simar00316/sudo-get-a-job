# Install sudo-get-a-job (instructions for the coding agent)

You are a coding agent (Claude Code, Codex, or similar) setting this up for the user. Run each step, check its output, and fix problems before moving on. Explain what you are doing in one short line per step.

## 1. Make sure `uv` exists

Run `uv --version`. If it is missing, install it:

- macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Open a new shell or add uv's bin directory to `PATH` if `uv` is still not found.

## 2. Install the CLI

```bash
uv tool install --python 3.12 --upgrade "git+https://github.com/Simar00316/sudo-get-a-job"
sgaj --help
```

If `sgaj` is not found, run `uv tool update-shell`, then use a new shell.

## 3. Install the skill

```bash
sgaj install-skill
```

This copies the skill to `~/.claude/skills/sudo-get-a-job/` (and `~/.codex/skills/sudo-get-a-job/` when Codex is installed). Other agents: pass `--dest <their skills dir>/sudo-get-a-job`.

## 4. Connect Chrome

```bash
sgaj doctor
```

If it prints setup steps, ask the user to open `chrome://inspect/#remote-debugging` in Chrome and enable **Allow remote debugging for this browser instance**. Run `sgaj doctor` again. If Chrome shows an **Allow** prompt, the user clicks it once.

## 5. Start

Read the installed `SKILL.md` and follow its "Start of every session" section. With no profile yet, that starts onboarding: a few questions, the user's resume, and signing in to job sites in their own Chrome.

If the agent does not list the skill automatically, tell the user it will load after restarting the agent. You can keep going now by following the `SKILL.md` you just read.

## Updating later

```bash
uv tool upgrade sudo-get-a-job && sgaj install-skill
```
