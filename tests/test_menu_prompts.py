from __future__ import annotations

import builtins
import sys
from pathlib import Path

# pdfsuite lives in ../src, which is not on sys.path for `python tests/...` or pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdfsuite import _prompt_output, _prompt_path_list, _strip_quotes, interactive_menu  # noqa: E402


def _feed(monkeypatch, answers: list[str]) -> None:
    """Make input() return the given answers in order (EOFError when they run out)."""
    it = iter(answers)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(builtins, "input", fake_input)


def test_strip_quotes() -> None:
    assert _strip_quotes('"C:\\My Files\\a.pdf"') == "C:\\My Files\\a.pdf"
    assert _strip_quotes("'a.pdf'") == "a.pdf"
    assert _strip_quotes("a.pdf") == "a.pdf"
    assert _strip_quotes('"a.pdf') == '"a.pdf'
    assert _strip_quotes('"') == '"'


def test_prompt_path_list_strips_each_item(monkeypatch) -> None:
    _feed(monkeypatch, ['"a.pdf", \'b c.pdf\' ,c.pdf'])
    assert _prompt_path_list("Inputs") == ["a.pdf", "b c.pdf", "c.pdf"]


def test_prompt_path_list_keeps_commas_inside_quotes(monkeypatch) -> None:
    # "Copy as path" output for two files, the first with a comma in its name.
    _feed(monkeypatch, ['"C:\\Docs\\Invoice, March.pdf","C:\\Docs\\b.pdf"'])
    assert _prompt_path_list("Inputs") == ["C:\\Docs\\Invoice, March.pdf", "C:\\Docs\\b.pdf"]
    _feed(monkeypatch, ['"a, b.pdf" , c.pdf,d.pdf'])
    assert _prompt_path_list("Inputs") == ["a, b.pdf", "c.pdf", "d.pdf"]


def test_prompt_output_refuses_input_and_confirms_overwrite(monkeypatch, tmp_path) -> None:
    src = tmp_path / "in.pdf"
    existing = tmp_path / "existing.pdf"
    src.write_bytes(b"x")
    existing.write_bytes(b"y")
    new = tmp_path / "new.pdf"

    # Same as input -> re-ask; blank -> re-ask; existing + "n" -> re-ask; new name accepted.
    _feed(monkeypatch, [f'"{src}"', "", str(existing), "n", str(new)])
    assert _prompt_output("Output", inputs=[str(src)]) == str(new)

    _feed(monkeypatch, [str(existing), "y"])
    assert _prompt_output("Output", inputs=[str(src)]) == str(existing)


def test_prompt_output_resolves_against_base_dir(monkeypatch, tmp_path) -> None:
    (tmp_path / "merged_output.pdf").write_bytes(b"x")
    # Blank -> default, which exists inside base_dir -> asks to overwrite; decline, then pick another.
    _feed(monkeypatch, ["", "n", "other.pdf"])
    assert _prompt_output("Output", default="merged_output.pdf", base_dir=str(tmp_path)) == "other.pdf"


def test_menu_returns_to_menu_after_a_job(monkeypatch, tmp_path) -> None:
    missing = tmp_path / "missing.pdf"
    # Job 19 fails (file missing), Enter returns to the menu, then 0 exits.
    _feed(monkeypatch, ["19", str(missing), "", "0"])
    assert interactive_menu() == 0
