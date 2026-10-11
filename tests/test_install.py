from sudo_get_a_job.install import default_destinations, install_skill


def test_installs_skill_and_replaces_old_copy(tmp_path):
    dest = tmp_path / "skills" / "sudo-get-a-job"
    (dest / "references").mkdir(parents=True)
    (dest / "references" / "stale.md").write_text("old")
    assert install_skill([dest]) == [dest]
    assert (dest / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: sudo-get-a-job")
    assert (dest / "references" / "apply.md").is_file()
    assert not (dest / "references" / "stale.md").exists()


def test_codex_destination_only_when_codex_is_installed(tmp_path):
    assert [d.parts[-3] for d in default_destinations(tmp_path)] == [".claude"]
    (tmp_path / ".codex").mkdir()
    assert [d.parts[-3] for d in default_destinations(tmp_path)] == [".claude", ".codex"]
