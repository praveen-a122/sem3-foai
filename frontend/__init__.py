"""
Frontend Serious Game & Telemetry Engine Package
"""
from .telemetry_logger import TelemetryLogger
from .ui_assets import COLORS, CARD_SYMBOLS, FONT_FAMILY, FONT_SIZES, get_symbols_for_pairs

__all__ = ["TelemetryLogger", "COLORS", "CARD_SYMBOLS", "FONT_FAMILY", "FONT_SIZES", "get_symbols_for_pairs"]
