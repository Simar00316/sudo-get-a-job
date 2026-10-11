"""Copy the bundled agent skill to where coding agents look for skills."""

import shutil
from pathlib import Path


def skill_source():
    packaged = Path(__file__).with_name("skill")  # inside an installed wheel
    return packaged if packaged.is_dir() else Path(__file__).parent.parent / "skill"  # source checkout


def default_destinations(home=None):
    home = Path(home or Path.home())
    dests = [home / ".claude" / "skills" / "sudo-get-a-job"]
    if (home / ".codex").is_dir():
        dests.append(home / ".codex" / "skills" / "sudo-get-a-job")
    return dests


def install_skill(dests=None):
    src = skill_source()
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"Skill files not found at {src}. Reinstall sudo-get-a-job.")
    done = []
    for dest in dests or default_destinations():
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)  # upgrades replace the previous copy wholesale
        shutil.copytree(src, dest)
        done.append(dest)
    return done
