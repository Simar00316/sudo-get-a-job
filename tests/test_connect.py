import socket

import pytest

from sudo_get_a_job.connect import HOWTO, find_ws


def write_port(d, port):
    d.mkdir(parents=True)
    (d / "DevToolsActivePort").write_text(f"{port}\n/devtools/browser/abc\n")


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("SGAJ_CDP_WS", "ws://127.0.0.1:1/devtools/browser/x")
    assert find_ws([tmp_path]) == "ws://127.0.0.1:1/devtools/browser/x"


def test_skips_stale_profile_and_picks_live_one(monkeypatch, tmp_path):
    monkeypatch.delenv("SGAJ_CDP_WS", raising=False)
    with socket.socket() as live:
        live.bind(("127.0.0.1", 0))
        live.listen()
        stale = socket.socket()
        stale.bind(("127.0.0.1", 0))
        dead_port = stale.getsockname()[1]
        stale.close()
        write_port(tmp_path / "chrome", dead_port)
        write_port(tmp_path / "edge", live.getsockname()[1])
        assert find_ws([tmp_path / "chrome", tmp_path / "edge"]) == (
            f"ws://127.0.0.1:{live.getsockname()[1]}/devtools/browser/abc"
        )


def test_no_profile_explains_how_to_enable(monkeypatch, tmp_path):
    monkeypatch.delenv("SGAJ_CDP_WS", raising=False)
    with pytest.raises(SystemExit) as e:
        find_ws([tmp_path / "missing"])
    assert str(e.value) == HOWTO


def test_pending_allow_prompt_gives_instructions_not_a_traceback(monkeypatch):
    import browser_harness.admin

    from sudo_get_a_job import connect

    def handshake_timeout(**_):
        raise RuntimeError("fatal: CDP WS handshake failed: timed out during opening handshake")

    monkeypatch.setenv("SGAJ_CDP_WS", "ws://127.0.0.1:1/devtools/browser/x")
    monkeypatch.setattr(browser_harness.admin, "ensure_daemon", handshake_timeout)
    with pytest.raises(SystemExit) as e:
        connect.connect()
    assert "click Allow" in str(e.value)
