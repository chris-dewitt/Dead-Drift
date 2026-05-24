from __future__ import annotations


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
