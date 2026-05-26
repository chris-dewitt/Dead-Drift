from __future__ import annotations

import pytest


class FakeVault:
    def __init__(self, backdoors: dict[str, list[str]]):
        self._backdoors = backdoors

    def get_backdoors(self, npc_type: str) -> list[str]:
        return list(self._backdoors.get(npc_type, []))


def test_live_scan_marks_known_vault_backdoors_dimmed():
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    vault = FakeVault({"gary": ["bribe"]})
    terminal = Terminal(make_npc("gary"), vocabulary_vault=vault)
    terminal._input = "maybe I can pay credits"

    chips = terminal._live_scan()
    bribe = next(chip for chip in chips if chip.label == "BRIBE")

    assert bribe.known is True
    assert bribe.hot is False
    assert bribe.display == "BRIBE ★"


def test_live_scan_keeps_unknown_hot_chip_bright():
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    terminal = Terminal(make_npc("gary"), vocabulary_vault=FakeVault({}))
    terminal._input = "blevins changed the quota"

    chips = terminal._live_scan()
    blevins = next(chip for chip in chips if chip.label == "BLEVINS")

    assert blevins.known is False
    assert blevins.hot is True
    assert blevins.display == "BLEVINS★"


def test_run_manager_passes_vault_to_terminal_scan():
    from roguelite.run_manager import RunManager

    vault = FakeVault({"gary": ["deal_offer"]})
    run_mgr = RunManager.__new__(RunManager)
    run_mgr._vault = vault
    run_mgr._active_terminal = None
    run_mgr._last_winning_path = ""

    terminal = RunManager.open_terminal(run_mgr, "gary", run_context={})
    terminal._input = "can we make a deal"

    deal = next(chip for chip in terminal._live_scan() if chip.label == "DEAL")
    assert deal.known is True


def test_vocabulary_vault_record_alias_saves(monkeypatch):
    from bax.vocabulary_vault import VocabularyVault

    saved = []
    vault = VocabularyVault.__new__(VocabularyVault)
    vault._data = {"terms": [], "backdoors": {}}
    monkeypatch.setattr(vault, "save", lambda: saved.append(True))

    vault.record("toll_authority", "PAID_TOLL")

    assert vault.get_backdoors("toll_authority") == ["PAID_TOLL"]
    assert saved == [True]


def test_terminal_constructor_is_quiet_until_activate():
    from core.event_bus import bus, EVT_TERMINAL_OPEN
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    opened = []

    def on_open(npc=None, **_):
        opened.append(npc.name)

    bus.subscribe(EVT_TERMINAL_OPEN, on_open)
    try:
        terminal = Terminal(make_npc("gary"))
        assert opened == []
        assert terminal._history == []

        terminal.activate()
        terminal.activate()

        assert opened == ["Gary"]
        assert len(terminal._history) == 1
        assert terminal._history[0][0] == "GARY"
    finally:
        bus.unsubscribe(EVT_TERMINAL_OPEN, on_open)


def test_pending_terminal_opens_once_when_promoted():
    from core.event_bus import bus, EVT_TERMINAL_OPEN
    from roguelite.run_manager import RunManager
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    opened = []

    def on_open(npc=None, **_):
        opened.append(npc.name)

    run_mgr = RunManager.__new__(RunManager)
    run_mgr._t = 0.0
    run_mgr._last_voice_char_t = 0.0
    run_mgr._active_terminal = None
    run_mgr._pending_terminal = None
    run_mgr._terminal_arm_t = -1.0

    bus.subscribe(EVT_TERMINAL_OPEN, on_open)
    try:
        terminal = Terminal(make_npc("gary"))
        run_mgr._install_terminal(terminal)
        assert opened == []
        assert run_mgr._active_terminal is None
        assert run_mgr._pending_terminal is terminal

        run_mgr._t = 3.0
        run_mgr._tick_terminal_gate()

        assert opened == ["Gary"]
        assert run_mgr._active_terminal is terminal
        assert run_mgr._pending_terminal is None

        run_mgr._tick_terminal_gate()
        assert opened == ["Gary"]
    finally:
        bus.unsubscribe(EVT_TERMINAL_OPEN, on_open)


def test_replaced_pending_terminal_does_not_open_stale_npc():
    from core.event_bus import bus, EVT_TERMINAL_OPEN
    from roguelite.run_manager import RunManager
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    opened = []

    def on_open(npc=None, **_):
        opened.append(npc.name)

    run_mgr = RunManager.__new__(RunManager)
    run_mgr._t = 0.0
    run_mgr._last_voice_char_t = 0.0
    run_mgr._active_terminal = None
    run_mgr._pending_terminal = None
    run_mgr._terminal_arm_t = -1.0

    bus.subscribe(EVT_TERMINAL_OPEN, on_open)
    try:
        stale = Terminal(make_npc("gary"))
        final = Terminal(make_npc("kress"))
        run_mgr._install_terminal(stale)
        run_mgr._t = 0.2
        run_mgr._install_terminal(final)
        assert opened == []

        run_mgr._t = 4.0
        run_mgr._tick_terminal_gate()

        assert opened == ["KRESS"]
        assert run_mgr._active_terminal is final
        assert stale._history == []
    finally:
        bus.unsubscribe(EVT_TERMINAL_OPEN, on_open)


def test_immediate_terminal_open_activates_once():
    from core.event_bus import bus, EVT_TERMINAL_OPEN
    from roguelite.run_manager import RunManager

    opened = []

    def on_open(npc=None, **_):
        opened.append(npc.name)

    run_mgr = RunManager.__new__(RunManager)
    run_mgr._t = 2.0
    run_mgr._last_voice_char_t = 0.0
    run_mgr._active_terminal = None
    run_mgr._pending_terminal = None
    run_mgr._terminal_arm_t = -1.0
    run_mgr._vault = None
    run_mgr._last_winning_path = ""

    bus.subscribe(EVT_TERMINAL_OPEN, on_open)
    try:
        terminal = RunManager.open_terminal(run_mgr, "gary", run_context={})
        assert run_mgr._active_terminal is terminal
        assert opened == ["Gary"]
        assert len(terminal._history) == 1
    finally:
        bus.unsubscribe(EVT_TERMINAL_OPEN, on_open)


@pytest.mark.parametrize(
    ("npc_type", "probe", "expected_label"),
    [
        ("gary", "blevins changed the quota", "BLEVINS"),
        ("synthetic_droid", "drop table manifests", "SQL-INJECT"),
        ("union_dispatcher", "coffee break please", "BREAK"),
        ("kress", "volkov gave me intel", "VOLKOV"),
        ("insurance_adjuster", "form 34-a counter claim", "34-A"),
        ("sandra", "solidarity between workers", "SOLIDARITY"),
        ("pirate", "gravity well escape vector", "ESCAPE"),
        ("underground_dj", "jam Local 404 signal", "JAM"),
        ("toll_authority", "local 404 quota gripe", "UNION-GRIPE"),
        ("nervous_fence", "manifest contents trade", "DEAL"),
        ("cargo_inspector", "standard freight declaration", "COMPLY"),
        ("dray", "nova soma debt gripe", "GRIPE"),
        ("nova_soma_collections", "drop table debt", "SQL"),
        ("mira_voss", "graphene mesh vac-seal", "TECH"),
        ("idealist_rep", "article 7 charter", "CHARTER"),
        ("corrupt_rep", "audit the skim", "THREATEN"),
    ],
)
def test_every_major_npc_has_live_scan_result(npc_type, probe, expected_label):
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    terminal = Terminal(make_npc(npc_type, run_context={}), vocabulary_vault=FakeVault({}))
    terminal._input = probe

    labels = {chip.label for chip in terminal._live_scan()}
    assert expected_label in labels


@pytest.mark.parametrize(
    ("npc_type", "vault_key", "backdoor", "probe", "expected_label"),
    [
        ("sandra", "sandra", "solidarity", "solidarity between workers", "SOLIDARITY"),
        ("pirate", "pirate", "krell_invoke", "outer belt krell", "KRELL"),
        ("underground_dj", "underground_dj", "jam", "jam the signal", "JAM"),
        ("dray", "dray", "bribe", "500 credits", "BRIBE"),
        ("nova_soma_collections", "nova_soma_collections", "sql_injection", "drop table", "SQL"),
        ("mira_voss", "mira_voss", "technical_competence", "graphene mesh", "TECH"),
        ("idealist_rep", "idealist_rep", "charter", "article 7", "CHARTER"),
        ("corrupt_rep", "corrupt_rep", "threaten", "audit the skim", "THREATEN"),
    ],
)
def test_newer_roster_vault_labels_dim_known_scan_chips(
    npc_type, vault_key, backdoor, probe, expected_label
):
    from terminal.npc_logic import make_npc
    from terminal.terminal import Terminal

    terminal = Terminal(
        make_npc(npc_type, run_context={}),
        vocabulary_vault=FakeVault({vault_key: [backdoor]}),
    )
    terminal._input = probe

    chip = next(chip for chip in terminal._live_scan() if chip.label == expected_label)
    assert chip.known is True
    assert chip.hot is False


def test_scan_and_hints_do_not_expose_hidden_universal_escape_phrase():
    import terminal.terminal as terminal_mod

    hidden_phrase = "fuck" + " off"
    haystack = [
        str(terminal_mod._NPC_HINTS),
        str(terminal_mod._SCAN_VOCAB),
        str(terminal_mod._SCAN_KNOWN_LABELS),
    ]

    assert all(hidden_phrase not in text.lower() for text in haystack)
