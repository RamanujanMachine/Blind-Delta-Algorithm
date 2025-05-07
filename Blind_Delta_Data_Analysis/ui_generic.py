# ────────────────────────────────────────────────────────────────
# ui_generic.py – Reusable console UI with coloured progress bar
# ────────────────────────────────────────────────────────────────

from __future__ import annotations

import sys
from typing import Any, Dict, List, Sequence


class BaseUI:  # pylint: disable=too-few-public-methods
    """Head‑less default UI. Override in concrete implementations."""

    # ── generic helpers ---------------------------------------------------
    def file_iterator(self, iterable: Sequence[Any], desc: str = ""):
        """Wrap an iterable (e.g. with tqdm).  Default: identity."""
        return iterable

    # ── coloured progress‑bar API ----------------------------------------
    def start_progress_bar(
        self,
        total: int,
        *,
        title: str = "",
        status_palette: Dict[str, str] | None = None,
    ) -> None:
        """Initialise an *in‑place* progress bar of *total* cells.

        `status_palette` maps *status* strings (passed to `update_progress_bar`)
        to *colour names* ("green", "red", "grey", …) or directly to the
        glyph that should be rendered for that status.  Concrete UIs decide
        how to colourise the glyph.
        """

    def update_progress_bar(self, index: int, status: str) -> None:  # noqa: D401
        """Paint cell *index* with *status* colour."""

    def finish_progress_bar(self, summary: Dict[str, List[Any]] | None = None):
        """Finalize the bar and (optionally) print a coloured summary."""


# ── Rich console implementation – uses *tqdm* + *colorama* --------------


class ConsoleUI(BaseUI):
    """Console UI with tqdm iterator + RGB block progress bar."""

    # --- optional deps (fallback‑safe) -----------------------------------
    try:
        from tqdm import tqdm  # type: ignore
    except ImportError:  # pragma: no cover – works without tqdm
        def tqdm(iterable=None, **_kw):  # type: ignore
            return iterable if iterable is not None else lambda x: x

    try:
        from colorama import Fore, Style, init  # type: ignore

        init(autoreset=True)
    except ImportError:  # pragma: no cover – plain output
        class _NoColour:  # pylint: disable=too-few-public-methods
            def __getattr__(self, _):
                return ""

        Fore = Style = _NoColour()  # type: ignore

    # --- glyphs ----------------------------------------------------------
    _BLOCK = "█"
    _EMPTY = "░"

    _COLOUR_TO_BLOCK = {
        "green": Fore.GREEN + _BLOCK + Style.RESET_ALL,  # type: ignore
        "red": Fore.RED + _BLOCK + Style.RESET_ALL,  # type: ignore
        "grey": Fore.LIGHTBLACK_EX + _BLOCK + Style.RESET_ALL,  # type: ignore
    }

    # --------------------------------------------------------------------
    # tqdm wrapper
    # --------------------------------------------------------------------
    def file_iterator(self, iterable: Sequence[Any], desc: str = ""):
        return self.tqdm(iterable, desc=desc, unit="file")  # type: ignore

    # --------------------------------------------------------------------
    # coloured progress bar
    # --------------------------------------------------------------------
    def start_progress_bar(
        self,
        total: int,
        *,
        title: str = "",
        status_palette: Dict[str, str] | None = None,
    ) -> None:
        self._total = total
        self._title = title or "Progress"
        # Default palette – can be overridden per call
        default_palette = {
            "added": "green",
            "ok": "green",
            "failed": "red",
            "error": "red",
            "unknown": "grey",
            "skip": "grey",
        }
        palette: Dict[str, str] = {**default_palette, **(status_palette or {})}

        # Convert colour names to coloured glyphs
        self._palette_blocks: Dict[str, str] = {
            status: (self._COLOUR_TO_BLOCK.get(col, col)) for status, col in palette.items()
        }
        self._cells: List[str] = [self._EMPTY] * total
        self._paint()

    def update_progress_bar(self, index: int, status: str) -> None:
        glyph = self._palette_blocks.get(status, self._COLOUR_TO_BLOCK.get("grey", self._EMPTY))
        if 0 <= index < len(self._cells):
            self._cells[index] = glyph
            self._paint()

    # ------------------------------------------------------------------
    def finish_progress_bar(self, summary=None):  # noqa: D401
        # newline after bar
        sys.stdout.write("\n")
        sys.stdout.flush()
        if not summary:
            return
        # pretty colourised summary line
        parts = []
        for status, items in summary.items():
            colour_code = {
                "added": self.Fore.GREEN,
                "failed": self.Fore.RED,
                "unknown": self.Fore.LIGHTBLACK_EX,
            }.get(status, "")
            reset = self.Style.RESET_ALL if hasattr(self, "Style") else ""
            parts.append(f"{colour_code}{len(items)} {status}{reset}")
        print(", ".join(parts))

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _paint(self):
        done = sum(c != self._EMPTY for c in self._cells)
        bar = "".join(self._cells)
        sys.stdout.write(f"\r{self._title}: [{bar}] {done}/{self._total}")
        sys.stdout.flush()