"""Keyboard overlay and Typing animation widgets."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import bisect, math, random
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QWidget

from .themes import THEMES, Theme

_US_SHIFT: Dict[str, str] = {
    "~": "`", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
    "&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=", "{": "[",
    "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",", ">": ".", "?": "/",
}

_QWERTY_ROWS = [
    [("`", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("Bksp", 2)],
    [("Tab", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1), ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 1.5)],
    [("Caps", 1.75), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1), ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("Enter", 2.25)],
    [("Shift", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1), ("M", 1), (",", 1), (".", 1), ("/", 1), ("Shift", 2.75)],
    [("Ctrl", 1.25), ("Win", 1.25), ("Alt", 1.25), ("", 6.25), ("Alt", 1.25), ("Fn", 1.25), ("Menu", 1.25), ("Ctrl", 1.25)],
]
_DVORAK_ROWS = [
    [("`", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("[", 1), ("]", 1), ("Bksp", 2)],
    [("Tab", 1.5), ("'", 1), (",", 1), (".", 1), ("P", 1), ("Y", 1), ("F", 1), ("G", 1), ("C", 1), ("R", 1), ("L", 1), ("/", 1), ("=", 1), ("\\", 1.5)],
    [("Caps", 1.75), ("A", 1), ("O", 1), ("E", 1), ("U", 1), ("I", 1), ("D", 1), ("H", 1), ("T", 1), ("N", 1), ("S", 1), ("-", 1), ("Enter", 2.25)],
    [("Shift", 2.25), (";", 1), ("Q", 1), ("J", 1), ("K", 1), ("X", 1), ("B", 1), ("M", 1), ("W", 1), ("V", 1), ("Z", 1), ("Shift", 2.75)],
    [("Ctrl", 1.25), ("Win", 1.25), ("Alt", 1.25), ("", 6.25), ("Alt", 1.25), ("Fn", 1.25), ("Menu", 1.25), ("Ctrl", 1.25)],
]
_COLEMAK_ROWS = [
    [("`", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("Bksp", 2)],
    [("Tab", 1.5), ("Q", 1), ("W", 1), ("F", 1), ("P", 1), ("G", 1), ("J", 1), ("L", 1), ("U", 1), ("Y", 1), (";", 1), ("[", 1), ("]", 1), ("\\", 1.5)],
    [("Bksp", 1.75), ("A", 1), ("R", 1), ("S", 1), ("T", 1), ("D", 1), ("H", 1), ("N", 1), ("E", 1), ("I", 1), ("O", 1), ("'", 1), ("Enter", 2.25)],
    [("Shift", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("K", 1), ("M", 1), (",", 1), (".", 1), ("/", 1), ("Shift", 2.75)],
    [("Ctrl", 1.25), ("Win", 1.25), ("Alt", 1.25), ("", 6.25), ("Alt", 1.25), ("Fn", 1.25), ("Menu", 1.25), ("Ctrl", 1.25)],
]

KEYBOARD_LAYOUTS: Dict[str, Dict] = {
    "QWERTY": {"description": "Standard US QWERTY layout", "rows": _QWERTY_ROWS, "shift_map": _US_SHIFT},
    "Dvorak": {"description": "Dvorak ergonomic layout", "rows": _DVORAK_ROWS, "shift_map": _US_SHIFT},
    "Colemak": {"description": "Colemak ergonomic layout", "rows": _COLEMAK_ROWS, "shift_map": _US_SHIFT},
}

def _build_char_map(layout_name: str) -> Dict[str, Tuple[int, int]]:
    ld = KEYBOARD_LAYOUTS[layout_name]; cm: Dict[str, Tuple[int, int]] = {}
    for ri, row in enumerate(ld["rows"]):
        for ci, (label, w) in enumerate(row):
            ll = label.lower()
            if len(label) == 1: cm[label] = cm[ll] = cm[label.upper()] = (ri, ci)
            if ll == "space" or (label == "" and w >= 4): cm[" "] = (ri, ci)
            elif "enter" in ll: cm["\n"] = (ri, ci)
            elif "tab" in ll: cm["\t"] = (ri, ci)
            elif "bksp" in ll: cm["\x08"] = (ri, ci)
    for shifted, base in ld.get("shift_map", {}).items():
        if base in cm: cm[shifted] = cm[base]
    return cm

class KeyboardOverlay:
    __slots__ = ("video_w", "video_h", "layout_name", "theme", "opacity", "rows", "char_map",
                 "num_rows", "position", "key_unit", "key_gap", "key_h", "_max_units",
                 "_max_keys", "_kb_width", "_kb_height", "_kb_x", "_kb_y", "key_rects", "_bg_cache")

    def __init__(self, video_w: int, video_h: int, layout_name: str = "QWERTY",
                 theme: Optional[Theme] = None, opacity: float = 0.82,
                 max_height: Optional[int] = None, position: str = "bottom_center"):
        self.video_w = video_w; self.video_h = video_h
        self.layout_name = layout_name
        self.theme = theme if isinstance(theme, dict) else (theme.__dict__ if theme else THEMES["Dracula"].__dict__)
        self.opacity = opacity
        self.rows = KEYBOARD_LAYOUTS[layout_name]["rows"]
        self.char_map = _build_char_map(layout_name)
        self.num_rows = len(self.rows)
        self.position = position
        self.key_unit = max(20, int(video_w * 0.028))
        self.key_gap = max(2, self.key_unit // 14)
        self.key_h = int(self.key_unit * 0.82)

        if max_height and max_height > 0:
            natural_h = self.num_rows * self.key_h + (self.num_rows - 1) * self.key_gap
            if natural_h > max_height:
                lo, hi = 10, self.key_unit
                for _ in range(30):
                    mid = (lo + hi) / 2
                    tg = max(2, int(mid) // 14)
                    th = self.num_rows * int(mid * 0.82) + (self.num_rows - 1) * tg
                    if th > max_height: hi = mid
                    else: lo = mid
                self.key_unit = max(10, int(lo))
                self.key_gap = max(2, self.key_unit // 14)
                self.key_h = int(self.key_unit * 0.82)

        self._max_units = max(sum(w for _, w in row) for row in self.rows)
        self._max_keys = max(len(row) for row in self.rows)
        self._kb_width = int(self._max_units * self.key_unit + (self._max_keys - 1) * self.key_gap)
        self._kb_height = int(len(self.rows) * self.key_h + (len(self.rows) - 1) * self.key_gap)
        self._kb_x = (video_w - self._kb_width) // 2
        self._kb_y = video_h - self._kb_height - max(8, video_h // 60)
        self._apply_position()
        self.key_rects: Dict[Tuple[int, int], QRect] = {}
        self._rebuild_key_rects()
        self._bg_cache: Optional[QImage] = None
        self._build_bg_cache()

    def height_needed(self) -> int:
        return self._kb_height + max(8, self.video_h // 60) + max(6, self.video_h // 90)

    def _apply_position(self) -> None:
        m = max(8, self.video_h // 60)
        vw, vh, kw, kh = self.video_w, self.video_h, self._kb_width, self._kb_height
        match self.position:
            case "bottom_center": self._kb_x, self._kb_y = (vw - kw) // 2, vh - kh - m
            case "bottom_right": self._kb_x, self._kb_y = vw - kw - m, vh - kh - m
            case "bottom_left": self._kb_x, self._kb_y = m, vh - kh - m
            case "top_center": self._kb_x, self._kb_y = (vw - kw) // 2, m
            case "top_right": self._kb_x, self._kb_y = vw - kw - m, m
            case "top_left": self._kb_x, self._kb_y = m, m
            case "center_left": self._kb_x, self._kb_y = m, (vh - kh) // 2
            case "center_right": self._kb_x, self._kb_y = vw - kw - m, (vh - kh) // 2

    def _rebuild_key_rects(self) -> None:
        self.key_rects = {}
        for ri, row in enumerate(self.rows):
            x = self._kb_x
            for ci, (_, w) in enumerate(row):
                kw = int(w * self.key_unit) - self.key_gap
                y = self._kb_y + ri * (self.key_h + self.key_gap)
                self.key_rects[(ri, ci)] = QRect(x, y, kw, self.key_h)
                x += int(w * self.key_unit)
        self._bg_cache = None

    def reposition(self, y_below: int = 0) -> None:
        self._apply_position()
        self._rebuild_key_rects()

    def resolve_key(self, ch: str) -> Optional[Tuple[int, int]]:
        return self.char_map.get(ch)

    def _build_bg_cache(self) -> None:
        pad = max(6, self.key_unit // 4)
        w = self._kb_width + 2 * pad
        h = self._kb_height + 2 * pad
        self._bg_cache = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        self._bg_cache.fill(Qt.transparent)
        p = QPainter(self._bg_cache)
        p.setRenderHint(QPainter.Antialiasing)
        th = self.theme
        radius = max(3, self.key_unit // 8)
        p.setPen(QPen(QColor(th["window_border"]), max(1, self.key_unit // 20)))
        p.setBrush(QColor(th["background"]))
        p.drawRoundedRect(0, 0, w, h, radius * 2, radius * 2)
        p.setFont(QFont("Arial", max(7, int(self.key_unit * 0.30))))
        for (ri, ci), rect in self.key_rects.items():
            label = self.rows[ri][ci][0]
            cache_rect = QRect(rect.x() - self._kb_x + pad, rect.y() - self._kb_y + pad,
                               rect.width(), rect.height())
            p.setBrush(QColor(th["title_bar"]))
            p.setPen(QColor(th["window_border"]))
            p.drawRoundedRect(cache_rect, radius, radius)
            if label:
                is_mod = len(label) > 1
                p.setPen(QColor(th["line_number"] if is_mod else th.get("foreground", "#f8f8f2")))
                p.drawText(cache_rect, Qt.AlignCenter, label)
        p.end()

    def draw(self, painter: QPainter, active_key: Optional[Tuple[int, int]] = None, flash: float = 0.0) -> None:
        painter.save()
        painter.setOpacity(self.opacity)
        if self._bg_cache is None: self._build_bg_cache()
        pad = max(6, self.key_unit // 4)
        painter.drawImage(self._kb_x - pad, self._kb_y - pad, self._bg_cache)
        if flash > 0 and active_key is not None:
            th = self.theme
            try: hl_base = QColor(th["cursor"])
            except KeyError: hl_base = QColor("#89b4fa")
            key_bg = QColor(th["title_bar"])
            flash_eased = 1.0 - (1.0 - flash) ** 2
            hl_fill = QColor(
                int(key_bg.red() + (hl_base.red() - key_bg.red()) * flash_eased),
                int(key_bg.green() + (hl_base.green() - key_bg.green()) * flash_eased),
                int(key_bg.blue() + (hl_base.blue() - key_bg.blue()) * flash_eased),
            )
            hl_glow = QColor(hl_base); hl_glow.setAlpha(int(60 * flash_eased))
            hl_expand = max(3, int(self.key_unit * 0.12 * flash_eased))
            rect = self.key_rects[active_key]
            radius = max(3, self.key_unit // 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hl_glow)
            painter.drawRoundedRect(rect.adjusted(-hl_expand, -hl_expand, hl_expand, hl_expand), radius, radius)
            painter.setBrush(hl_fill)
            painter.setPen(QColor(th["window_border"]))
            painter.drawRoundedRect(rect, radius, radius)
            label = self.rows[active_key[0]][active_key[1]][0]
            if label:
                is_mod = len(label) > 1
                painter.setPen(QColor(th["line_number"] if is_mod else th.get("foreground", "#f8f8f2")))
                painter.setFont(QFont("Arial", max(7, int(self.key_unit * 0.30))))
                painter.drawText(rect, Qt.AlignCenter, label)
        painter.restore()

Event = Tuple[float, int, str]

_QWERTY_POS: Dict[str, Tuple[int, int]] = {}
for _r, _row in enumerate(("`1234567890-=", "qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./")):
    for _c, _ch in enumerate(_row):
        _QWERTY_POS[_ch] = (_r, _c)
for _ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _QWERTY_POS[_ch] = _QWERTY_POS.get(_ch.lower(), (2, 0))

_QWERTY_NEARBY: Dict[str, str] = {
    'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wrsdf',
    'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujklo', 'j': 'huikmn',
    'k': 'jilpm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
    'q': 'wa', 'r': 'edft', 's': 'awedz', 't': 'rfgy', 'u': 'yhji', 'v': 'cfgb',
    'w': 'qasde', 'x': 'zsdc', 'y': 'tghu', 'z': 'asx', ' ': ' ',
}

@dataclass
class TypingProfile:
    name: str = "junior"
    wpm: int = 90
    pause_freq: float = 0.15
    start_pause: float = 0.5
    end_pause: float = 1.5
    auto_indent: bool = True
    error_chance: float = 0.03

class TypingAnimator:
    __slots__ = ("code", "profile", "base_delay", "display_chars",
                 "text_snapshots", "error_snapshots", "timeline", "_timestamps")

    def __init__(self, code: str, profile: TypingProfile, seed: Optional[int] = None):
        self.code = code
        self.profile = profile
        self.base_delay = 1.0 / ((profile.wpm * 5) / 60)
        self.display_chars: List[str] = []
        self.text_snapshots: List[str] = []
        self.error_snapshots: List[List[bool]] = []
        self.timeline: List[Event] = self._build(seed if seed is not None else 42)
        self._timestamps = [ts for ts, _, _ in self.timeline]

    def _get_typo(self, ch: str, rng: random.Random) -> str:
        lower = ch.lower()
        if lower in _QWERTY_NEARBY:
            typo = rng.choice(_QWERTY_NEARBY[lower])
            return typo.upper() if ch.isupper() else typo
        return ch

    def _build(self, seed: int) -> List[Event]:
        rng = random.Random(seed)
        t = self.profile.start_pause
        events: List[Event] = []
        p = self.profile
        i = 0
        current_text: List[str] = []
        current_errors: List[bool] = []
        self.text_snapshots.append("")
        self.error_snapshots.append([])

        def take_snapshot():
            self.text_snapshots.append("".join(current_text))
            self.error_snapshots.append(list(current_errors))

        while i < len(self.code):
            ch = self.code[i]
            d = self.base_delay * rng.uniform(0.6, 1.4)

            match ch:
                case "\n": d *= rng.uniform(2.0, 4.0)
                case " ": d *= rng.uniform(0.7, 1.3)
                case "\t": d *= rng.uniform(1.2, 1.8)
                case _:
                    if ch in "([{": d *= rng.uniform(1.1, 1.8)
                    elif ch in ")]}": d *= rng.uniform(0.9, 1.5)
                    elif ch in ",;:": d *= rng.uniform(1.3, 2.2)

            if i >= 1:
                pa = _QWERTY_POS.get(self.code[i - 1].lower())
                pb = _QWERTY_POS.get(ch.lower())
                if pa and pb:
                    dist = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                    if dist < 0.5: d *= 0.7
                    elif dist > 4: d *= 1.15

            if ch == ":" and i > 0:
                if "def " in self.code[max(0, i - 10):i] or "class " in self.code[max(0, i - 10):i]:
                    if rng.random() < 0.6: d += rng.uniform(2.0, 5.0)
            elif ch == ":":
                if rng.random() < 0.2: d += rng.uniform(1.0, 2.5)

            if ch in ("\n", ":"):
                if rng.random() < p.pause_freq: d += rng.uniform(0.4, 1.2)
            elif rng.random() < (p.pause_freq * 0.2):
                d += rng.uniform(0.3, 0.8)

            if rng.random() < 0.012: d += rng.uniform(0.4, 1.4)

            if ch.isalpha() and rng.random() < p.error_chance and i + 1 < len(self.code):
                typo_ch = self._get_typo(ch, rng)
                if typo_ch != ch:
                    current_text.append(typo_ch)
                    current_errors.append(True)
                    self.display_chars.append(typo_ch)
                    events.append((t, len(self.display_chars) - 1, typo_ch))
                    take_snapshot()
                    t += max(d * 0.5, 0.012) + rng.uniform(0.05, 0.15)
                    current_text.append("\b")
                    current_errors.append(False)
                    self.display_chars.append("\b")
                    events.append((t, len(self.display_chars) - 1, "\b"))
                    take_snapshot()
                    t += max(d * 0.3, 0.008)

            current_text.append(ch)
            current_errors.append(False)
            self.display_chars.append(ch)
            events.append((t, len(self.display_chars) - 1, ch))
            take_snapshot()
            t += max(d, 0.012)
            i += 1

            if p.auto_indent and ch == "\n" and i < len(self.code):
                indent = ""
                while i < len(self.code) and self.code[i] in (' ', '\t'):
                    indent += self.code[i]
                    i += 1
                if indent:
                    for ind_ch in indent:
                        current_text.append(ind_ch)
                        current_errors.append(False)
                        self.display_chars.append(ind_ch)
                        events.append((t, len(self.display_chars) - 1, ind_ch))
                        take_snapshot()
                        t += max(d * 0.3, 0.008)
        return events

    def duration(self) -> float:
        return (self.timeline[-1][0] + self.profile.end_pause
                if self.timeline else self.profile.start_pause + self.profile.end_pause)

    def visible_at(self, t: float) -> int:
        if t < self.profile.start_pause: return 0
        idx = bisect.bisect_right(self._timestamps, t)
        return self.timeline[idx - 1][1] + 1 if idx > 0 else 0

    def char_timestamps(self) -> List[Tuple[float, str]]:
        return [(ts, ch) for ts, _, ch in self.timeline if ch != "\b"]

    def active_key_at(self, t: float, flash_duration: float = 0.18) -> Tuple[Optional[str], float]:
        if not self._timestamps: return (None, 0.0)
        idx = bisect.bisect_right(self._timestamps, t)
        if idx == 0: return (None, 0.0)
        char = self.timeline[idx - 1][2]
        dt = t - self.timeline[idx - 1][0]
        return (char, max(0.0, 1.0 - dt / flash_duration)) if dt < flash_duration else (None, 0.0)
