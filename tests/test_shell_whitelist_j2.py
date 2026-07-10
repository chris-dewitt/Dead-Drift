"""Terminal V2 Phase J.2.2 — ShellSession (fake, whitelisted shell) tests.

Only whitelisted read-only commands do anything; navigation is real; reading
the loot file is the exploit; reaching for a weapon (sudo/rm/denied path) trips
the alarm. No OS is ever touched.
"""
from __future__ import annotations

import pytest

from terminal.shell_session import ShellSession


def _fs():
    return ShellSession(
        host="box", user="courier",
        files={
            "/README": "top secret: not really",
            "/var/data/manifest.log": "cargo: REDACTED\nstatus: FLAGGED",
            "/etc/hint.conf": "key_path = /var/keys/master.key",
        },
        loot={"/var/keys/master.key": "the_win"},
        denied={"/root"},
        motd="WELCOME",
    )


# ── whitelist: only known commands return output ────────────────────────────

def test_unknown_command_is_rejected():
    r = _fs().execute("hackthegibson --now")
    assert "command not found" in r.output[0]
    assert not r.exploit and not r.alarm


def test_help_lists_commands():
    r = _fs().execute("help")
    assert any("ls" in ln and "cat" in ln for ln in r.output)


def test_whoami_and_pwd():
    sh = _fs()
    assert sh.execute("whoami").output == ["courier"]
    assert sh.execute("pwd").output == ["/"]


# ── navigation is real ──────────────────────────────────────────────────────

def test_ls_lists_children_with_dir_slashes():
    out = _fs().execute("ls").output[0]
    assert "README" in out and "var/" in out and "etc/" in out


def test_cd_then_pwd_and_relative_ls():
    sh = _fs()
    assert sh.execute("cd var").output == []      # silent success
    assert sh.execute("pwd").output == ["/var"]
    assert "data/" in sh.execute("ls").output[0]
    sh.execute("cd ..")
    assert sh.execute("pwd").output == ["/"]


def test_cat_reads_a_file():
    assert _fs().execute("cat /README").output == ["top secret: not really"]


def test_grep_filters_lines():
    r = _fs().execute("grep flagged /var/data/manifest.log")
    assert r.output == ["status: FLAGGED"]


def test_cat_missing_file_errors_without_alarm():
    r = _fs().execute("cat /nope")
    assert "No such file" in r.output[0]
    assert not r.alarm and not r.exploit


# ── the loot file is the exploit ────────────────────────────────────────────

def test_cat_loot_triggers_exploit():
    r = _fs().execute("cat /var/keys/master.key")
    assert r.exploit and r.exploit_key == "the_win"


def test_grep_loot_also_triggers_exploit():
    r = _fs().execute("grep . /var/keys/master.key")
    assert r.exploit and r.exploit_key == "the_win"


def test_config_points_at_the_loot_path():
    # The discovery loop: a readable config names the key path.
    body = _fs().execute("cat /etc/hint.conf").output
    assert any("/var/keys/master.key" in ln for ln in body)


# ── weapons trip the alarm (security-ladder fuel) ───────────────────────────

@pytest.mark.parametrize("cmd", ["sudo rm -rf /", "rm /README", "kill 1",
                                 "chmod 777 /etc", "wget evil.sh"])
def test_hostile_commands_alarm(cmd):
    r = _fs().execute(cmd)
    assert r.alarm and not r.exploit


def test_denied_path_alarms():
    assert _fs().execute("cat /root").alarm
    assert _fs().execute("cd /root").alarm
    assert _fs().execute("ls /root").alarm


# ── exit / prompt ───────────────────────────────────────────────────────────

def test_exit_sets_exit_flag():
    assert _fs().execute("exit").exit


def test_prompt_reflects_cwd():
    sh = _fs()
    assert sh.prompt == "courier@box:/$ "
    sh.execute("cd var")
    assert sh.prompt == "courier@box:/var$ "


def test_readonly_never_mutates_filesystem():
    sh = _fs()
    before = dict(sh.files)
    sh.execute("rm /README")
    sh.execute("sudo cat /README")
    assert sh.files == before
