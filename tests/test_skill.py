"""The skill is documentation the agent executes. Keep it consistent with the CLI."""

import argparse
import re
from pathlib import Path

from sudo_get_a_job.cli import parser

SKILL = Path(__file__).parent.parent / "skill"
DOCS = {p.relative_to(SKILL).as_posix(): p.read_text(encoding="utf-8") for p in SKILL.rglob("*.md")}


def subcommands(p):
    action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return action.choices


def test_frontmatter_has_name_and_trigger_description():
    head = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", DOCS["SKILL.md"])
    assert head and head[1] == "sudo-get-a-job"
    assert 100 < len(head[2]) < 1024 and "apply" in head[2]


def test_referenced_files_exist():
    for doc, text in DOCS.items():
        for ref in re.findall(r"`((?:references/)?[\w-]+\.md)`", text):
            assert ref in DOCS or f"references/{ref}" in DOCS or ref in {"profile.md", "applications.md"}, \
                f"{doc} references missing {ref}"


def test_every_sgaj_command_in_the_docs_exists():
    commands = subcommands(parser())
    tracks = subcommands(commands["track"])
    for doc, text in DOCS.items():
        for cmd, sub in re.findall(r"sgaj (\w+)(?: (\w+))?", text):
            assert cmd in commands, f"{doc}: sgaj {cmd} does not exist"
            if cmd == "track" and sub:
                assert sub in tracks, f"{doc}: sgaj track {sub} does not exist"
