"""Theme registry and definitions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import threading

@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    background: str; foreground: str; comment: str; keyword: str; string: str
    number: str; function: str; builtin: str; decorator: str; operator: str
    class_name: str; line_number: str; current_line: str; cursor: str
    title_bar: str; title_text: str; window_border: str
    junior_accent: str = "#7aa2f7"
    senior_accent: str = "#9ece6a"

class ThemeRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._themes: Dict[str, Theme] = {}
                    cls._instance._load_defaults()
        return cls._instance

    def _load_defaults(self) -> None:
        raw = {
            "Dracula": {"background": "#282a36", "foreground": "#f8f8f2", "comment": "#6272a4", "keyword": "#ff79c6", "string": "#f1fa8c", "number": "#bd93f9", "function": "#50fa7b", "builtin": "#8be9fd", "decorator": "#50fa7b", "operator": "#ff79c6", "class_name": "#8be9fd", "line_number": "#6272a4", "current_line": "#44475a", "cursor": "#f8f8f2", "title_bar": "#21222c", "title_text": "#8be9fd", "window_border": "#191a21", "junior_accent": "#8be9fd", "senior_accent": "#50fa7b"},
            "Tokyo Night": {"background": "#16171e", "foreground": "#c0caf5", "comment": "#565f89", "keyword": "#bb9af7", "string": "#9ece6a", "number": "#ff9e64", "function": "#7aa2f7", "builtin": "#7aa2f7", "decorator": "#e0af68", "operator": "#89ddff", "class_name": "#7dcfff", "line_number": "#3b4261", "current_line": "#1a1b26", "cursor": "#c0caf5", "title_bar": "#1a1b26", "title_text": "#7aa2f7", "window_border": "#16171e", "junior_accent": "#7aa2f7", "senior_accent": "#9ece6a"},
            "One Dark": {"background": "#282c34", "foreground": "#abb2bf", "comment": "#5c6370", "keyword": "#c678dd", "string": "#98c379", "number": "#d19a66", "function": "#61afef", "builtin": "#e5c07b", "decorator": "#56b6c2", "operator": "#c678dd", "class_name": "#e5c07b", "line_number": "#4b5263", "current_line": "#2c313c", "cursor": "#528bff", "title_bar": "#21252b", "title_text": "#61afef", "window_border": "#181a1f", "junior_accent": "#61afef", "senior_accent": "#98c379"},
            "GitHub Dark": {"background": "#0d1117", "foreground": "#c9d1d9", "comment": "#8b949e", "keyword": "#ff7b72", "string": "#a5d6ff", "number": "#79c0ff", "function": "#d2a8ff", "builtin": "#ffa657", "decorator": "#ffa657", "operator": "#ff7b72", "class_name": "#ffa657", "line_number": "#484f58", "current_line": "#161b22", "cursor": "#58a6ff", "title_bar": "#010409", "title_text": "#58a6ff", "window_border": "#010409", "junior_accent": "#58a6ff", "senior_accent": "#7ee787"},
            "Monokai": {"background": "#272822", "foreground": "#f8f8f2", "comment": "#75715e", "keyword": "#f92672", "string": "#e6db74", "number": "#ae81ff", "function": "#a6e22e", "builtin": "#66d9ef", "decorator": "#a6e22e", "operator": "#f92672", "class_name": "#66d9ef", "line_number": "#75715e", "current_line": "#3e3d32", "cursor": "#f8f8f2", "title_bar": "#1e1f1c", "title_text": "#a6e22e", "window_border": "#1e1f1c", "junior_accent": "#66d9ef", "senior_accent": "#a6e22e"},
            "Solarized Dark": {"background": "#002b36", "foreground": "#839496", "comment": "#586e75", "keyword": "#859900", "string": "#2aa198", "number": "#d33682", "function": "#268bd2", "builtin": "#b58900", "decorator": "#cb4b16", "operator": "#859900", "class_name": "#b58900", "line_number": "#073642", "current_line": "#073642", "cursor": "#839496", "title_bar": "#073642", "title_text": "#268bd2", "window_border": "#002b36", "junior_accent": "#268bd2", "senior_accent": "#859900"},
            "VS Code Dark+": {"background": "#1e1e1e", "foreground": "#d4d4d4", "comment": "#6a9955", "keyword": "#569cd6", "string": "#ce9178", "number": "#b5cea8", "function": "#dcdcaa", "builtin": "#4ec9b0", "decorator": "#4ec9b0", "operator": "#d4d4d4", "class_name": "#4ec9b0", "line_number": "#858585", "current_line": "#2a2d2e", "cursor": "#aeafad", "title_bar": "#323233", "title_text": "#007acc", "window_border": "#323233", "junior_accent": "#569cd6", "senior_accent": "#dcdcaa"},
        }
        for name, d in raw.items():
            self._themes[name] = Theme(name=name, **d)

    def get(self, name: str) -> Theme:
        return self._themes.get(name, self._themes["Dracula"])

    def names(self) -> list:
        return list(self._themes.keys())

THEMES: Dict[str, Theme] = {name: ThemeRegistry().get(name) for name in ThemeRegistry().names()}
