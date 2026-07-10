"""Terminal V2 Phase J.2.2 — a fake, whitelisted shell.

This is NOT a real shell. It never touches the OS, never runs a subprocess,
never imports anything dynamic. It's a hand-authored playground: a per-NPC
in-memory filesystem plus a tiny whitelist of read-only commands. Players who
think in shells get `ls`, `cat`, `grep`, `cd`, `pwd`, `whoami`. Reading the
right "loot" file is the exploit. Reaching for a weapon — `sudo`, `rm`,
`kill`, `chmod`, or a permission-denied path — trips the alarm (the security
ladder counts those).

The Terminal drives it: `execute(line) -> ShellResult`. No pygame in here so
it unit-tests headless.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ShellResult:
    output: list[str] = field(default_factory=list)
    exploit: bool = False        # read the loot → player wins
    exit: bool = False           # typed `exit` → leave shell mode
    alarm: bool = False          # hostile op that failed → security ladder +1
    exploit_key: str = ""        # which exploit fired (for the vault/records)


# Commands that read as an intrusion attempt. They always "fail" (this is a
# read-only prop shell) and each one nudges the security ladder.
_HOSTILE_CMDS = {"sudo", "rm", "kill", "chmod", "mv", "dd", "mkfs", "shutdown",
                 "reboot", "wget", "curl", "nc", "ssh", "chown"}


def _norm(path: str) -> str:
    """Resolve a POSIX-ish path (absolute only after join) with . and .. ."""
    parts: list[str] = []
    for seg in path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/" + "/".join(parts)


class ShellSession:
    """A per-NPC read-only filesystem with a whitelisted command set."""

    def __init__(self, *, host: str = "unit", user: str = "courier",
                 files: dict[str, str] | None = None,
                 loot: dict[str, str] | None = None,
                 denied: set[str] | None = None,
                 motd: str = ""):
        self.host   = host
        self.user   = user
        self.files  = {_norm(k): v for k, v in (files or {}).items()}
        self.loot   = {_norm(k): v for k, v in (loot or {}).items()}
        self.denied = {_norm(k) for k in (denied or set())}
        self.motd   = motd
        self.cwd    = "/"
        self._looted: set[str] = set()

        # Every readable path (files + loot) contributes its parent dirs.
        self._dirs: set[str] = {"/"}
        for p in list(self.files) + list(self.loot) + list(self.denied):
            seg = ""
            for part in p.strip("/").split("/")[:-1]:
                seg = seg + "/" + part
                self._dirs.add(_norm(seg))

    # ------------------------------------------------------------------
    @property
    def prompt(self) -> str:
        cwd = self.cwd if self.cwd != "/" else "/"
        return f"{self.user}@{self.host}:{cwd}$ "

    def banner(self) -> list[str]:
        lines = [f"[shell] connected to {self.host} — read-only session."]
        if self.motd:
            lines.append(self.motd)
        lines.append("type `help` for commands · `exit` to drop back to comms")
        return lines

    # ------------------------------------------------------------------
    def _resolve(self, arg: str) -> str:
        return _norm(arg if arg.startswith("/") else self.cwd + "/" + arg)

    def _children(self, path: str) -> list[str]:
        path = _norm(path)
        prefix = "" if path == "/" else path
        seen: list[str] = []
        for coll in (self._dirs, set(self.files), set(self.loot)):
            for p in coll:
                if p == path:
                    continue
                if p.startswith(prefix + "/"):
                    rest = p[len(prefix) + 1:]
                    name = rest.split("/")[0]
                    entry = name + ("/" if (rest != name) or _norm(prefix + "/" + name) in self._dirs else "")
                    if entry not in seen:
                        seen.append(entry)
        return sorted(seen)

    # ------------------------------------------------------------------
    def execute(self, line: str) -> ShellResult:
        line = (line or "").strip()
        if not line:
            return ShellResult()
        if line in ("exit", "quit", "logout", ":q"):
            return ShellResult(output=["[shell] session closed."], exit=True)

        argv = line.split()
        cmd, args = argv[0].lower(), argv[1:]

        if cmd in _HOSTILE_CMDS:
            return ShellResult(
                output=[f"{cmd}: permission denied — this session is read-only.",
                        "*the connection logs your attempt*"],
                alarm=True)

        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler is None:
            return ShellResult(output=[f"{cmd}: command not found"])
        return handler(args)

    # ── whitelisted commands ─────────────────────────────────────────
    def _cmd_help(self, args) -> ShellResult:
        return ShellResult(output=[
            "available: ls  cat  grep  cd  pwd  whoami  clear  help  exit",
            "(read-only. the interesting files are not always in plain sight.)"])

    def _cmd_whoami(self, args) -> ShellResult:
        return ShellResult(output=[self.user])

    def _cmd_pwd(self, args) -> ShellResult:
        return ShellResult(output=[self.cwd])

    def _cmd_clear(self, args) -> ShellResult:
        return ShellResult(output=["\x0c"])   # Terminal treats as a soft clear marker

    def _cmd_ls(self, args) -> ShellResult:
        target = self._resolve(args[0]) if args else self.cwd
        if target in self.denied:
            return ShellResult(output=[f"ls: {target}: Permission denied"], alarm=True)
        if target in self.files or target in self.loot:
            return ShellResult(output=[target.rsplit("/", 1)[-1]])
        if target not in self._dirs:
            return ShellResult(output=[f"ls: {args[0] if args else target}: No such file or directory"])
        kids = self._children(target)
        return ShellResult(output=["  ".join(kids) if kids else "(empty)"])

    def _cmd_cd(self, args) -> ShellResult:
        if not args or args[0] == "~":
            self.cwd = "/"
            return ShellResult()
        target = self._resolve(args[0])
        if target in self.denied:
            return ShellResult(output=[f"cd: {args[0]}: Permission denied"], alarm=True)
        if target in self._dirs:
            self.cwd = target
            return ShellResult()
        if target in self.files or target in self.loot:
            return ShellResult(output=[f"cd: {args[0]}: Not a directory"])
        return ShellResult(output=[f"cd: {args[0]}: No such file or directory"])

    def _cmd_cat(self, args) -> ShellResult:
        if not args:
            return ShellResult(output=["cat: missing operand"])
        target = self._resolve(args[0])
        if target in self.denied:
            return ShellResult(output=[f"cat: {args[0]}: Permission denied"], alarm=True)
        if target in self.loot:
            self._looted.add(target)
            body = self.files.get(target, "")
            out = (body.splitlines() if body else [])
            return ShellResult(output=out, exploit=True, exploit_key=self.loot[target])
        if target in self.files:
            return ShellResult(output=self.files[target].splitlines() or [""])
        if target in self._dirs:
            return ShellResult(output=[f"cat: {args[0]}: Is a directory"])
        return ShellResult(output=[f"cat: {args[0]}: No such file or directory"])

    def _cmd_grep(self, args) -> ShellResult:
        if len(args) < 2:
            return ShellResult(output=["usage: grep PATTERN FILE"])
        pat = args[0].strip("'\"").lower()
        target = self._resolve(args[1])
        if target in self.denied:
            return ShellResult(output=[f"grep: {args[1]}: Permission denied"], alarm=True)
        body = self.files.get(target)
        is_loot = target in self.loot
        if body is None and not is_loot:
            return ShellResult(output=[f"grep: {args[1]}: No such file or directory"])
        hits = [ln for ln in (body or "").splitlines() if pat in ln.lower()]
        if is_loot:
            self._looted.add(target)
            return ShellResult(output=hits or ["(match)"], exploit=True,
                               exploit_key=self.loot[target])
        return ShellResult(output=hits)
