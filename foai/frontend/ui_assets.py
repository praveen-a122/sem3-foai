"""Accessible neutral/green/red UI assets and contrast helpers."""

from typing import Any, Dict, List, Tuple

COLORS = {
    "BACKGROUND": (31, 36, 30),
    "PANEL_BG": (43, 50, 40),
    "CARD_BACK": (75, 91, 62),
    "CARD_BACK_HOVER": (96, 113, 75),
    "CARD_FRONT_BG": (248, 249, 240),
    "TEXT_LIGHT": (255, 255, 255),
    "TEXT_MUTED": (210, 216, 194),
    "ACCENT_GOLD": (185, 195, 115),
    "SUCCESS_GREEN": (46, 120, 65),
    "ERROR_RED": (150, 45, 40),
    "BORDER_DEFAULT": (105, 115, 90),
    "BORDER_ACTIVE": (185, 195, 115),
}

FONT_FAMILY = "Arial"
FONT_SIZES = {
    "HEADER": 30,
    "SUBHEADER": 21,
    "CARD_SYMBOL": 42,
    "METRICS": 17,
}

_SYMBOL_COLORS = [
    (85, 50, 30),
    (90, 30, 35),
    (35, 85, 40),
    (95, 85, 20),
    (25, 85, 75),
    (75, 75, 65),
    (110, 45, 50),
    (70, 90, 35),
]

# Letters and digits render reliably across common Windows fonts.
CARD_SYMBOLS: List[Dict[str, Any]] = [
    {
        "symbol": character,
        "name": f"Symbol_{character}",
        "color": _SYMBOL_COLORS[index % len(_SYMBOL_COLORS)],
    }
    for index, character in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234")
]


def get_symbols_for_pairs(pair_count: int) -> List[Dict[str, Any]]:
    """Return pair_count distinct card symbols, generating more if necessary."""
    if pair_count < 0:
        raise ValueError("pair_count must not be negative")

    symbols = [dict(item) for item in CARD_SYMBOLS[:pair_count]]
    for index in range(len(symbols), pair_count):
        # Keep fallback glyphs distinct and font-compatible.
        label = str(index + 1)
        symbols.append({
            "symbol": label,
            "name": f"Symbol_{label}",
            "color": _SYMBOL_COLORS[index % len(_SYMBOL_COLORS)],
        })
    return symbols


def calculate_relative_luminance(color: Tuple[int, int, int]) -> float:
    """Calculate WCAG relative luminance for an RGB color."""
    def linearize(channel: int) -> float:
        value = channel / 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def calculate_contrast_ratio(
    foreground: Tuple[int, int, int],
    background: Tuple[int, int, int],
) -> float:
    """Calculate the WCAG contrast ratio between two RGB colors."""
    first = calculate_relative_luminance(foreground)
    second = calculate_relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def is_wcag_aa_compliant(
    foreground: Tuple[int, int, int],
    background: Tuple[int, int, int],
    large_text: bool = False,
) -> bool:
    threshold = 3.0 if large_text else 4.5
    return calculate_contrast_ratio(foreground, background) >= threshold


def is_wcag_aaa_compliant(
    foreground: Tuple[int, int, int],
    background: Tuple[int, int, int],
    large_text: bool = False,
) -> bool:
    threshold = 4.5 if large_text else 7.0
    return calculate_contrast_ratio(foreground, background) >= threshold
