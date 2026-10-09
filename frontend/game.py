"""
Interactive Pygame Serious Game: "Find the Pairs" Cognitive Assessment
======================================================================
Course: 22AIE201 - Fundamentals of AI
Team 3 Deliverable: Member 2 (Prahlad Vedhanarayanan - BL.SC.U4AIE25034)

Features:
- Built in Pygame / Pygame-CE following Jadhav & Vishwakarma (2026) and Sirály et al. (2015).
- Elder-friendly accessible layout (Mezrar & Bendella, 2022) with generous tile sizes and WCAG AAA contrast.
- Real-time sub-second telemetry logging with pause/resume latency tracking.
- Non-blocking live feedback loop decoupling Mesa ABM evaluation from the PyGame render loop.
- Atomic input guard (is_analyzing_telemetry) preventing race conditions during round transitions.
- Dynamic asset scaling with 30 distinct accessible symbols and permutation fallback generators.
- Headless / automated simulation mode for testing in non-display environments.
"""

import sys
import os
import time
import random
import threading
import pygame
from typing import List, Tuple, Dict, Any, Optional

from .ui_assets import COLORS, CARD_SYMBOLS, FONT_FAMILY, FONT_SIZES, get_symbols_for_pairs
from .telemetry_logger import TelemetryLogger
from .session_manager import SessionManager, ROUNDS_BY_DIFFICULTY

# Restrict the game UI to neutral, green, and red tones.
COLORS.update({
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
})


class Card:
    """Represents an individual card on the memory grid."""

    def __init__(self, idx: int, pair_id: int, symbol_meta: Dict[str, Any], rect: pygame.Rect):
        self.idx = idx
        self.pair_id = pair_id
        self.symbol_meta = symbol_meta
        self.rect = rect
        self.is_flipped = False
        self.is_matched = False
        self.hover = False

    def draw(self, surface: pygame.Surface, font_large: pygame.font.Font, font_small: pygame.font.Font):
        # Draw card background
        if self.is_matched:
            # Subtle dimming for matched cards
            pygame.draw.rect(surface, (45, 58, 43), self.rect, border_radius=12)
            pygame.draw.rect(surface, COLORS["SUCCESS_GREEN"], self.rect, width=3, border_radius=12)
            # Draw symbol in green
            sym_surf = font_large.render(self.symbol_meta["symbol"], True, COLORS["SUCCESS_GREEN"])
            sym_rect = sym_surf.get_rect(center=self.rect.center)
            surface.blit(sym_surf, sym_rect)
        elif self.is_flipped:
            # Card face open
            pygame.draw.rect(surface, COLORS["CARD_FRONT_BG"], self.rect, border_radius=12)
            pygame.draw.rect(surface, COLORS["BORDER_ACTIVE"], self.rect, width=3, border_radius=12)

            # Draw prominent colored symbol
            sym_surf = font_large.render(self.symbol_meta["symbol"], True, self.symbol_meta["color"])
            sym_rect = sym_surf.get_rect(center=(self.rect.centerx, self.rect.centery - 10))
            surface.blit(sym_surf, sym_rect)

            # Draw text label below symbol for accessibility
            clean_name = self.symbol_meta["name"].split("_")[0]
            name_surf = font_small.render(clean_name, True, (60, 60, 60))
            name_rect = name_surf.get_rect(center=(self.rect.centerx, self.rect.bottom - 18))
            surface.blit(name_surf, name_rect)
        else:
            # Card face down
            bg = COLORS["CARD_BACK_HOVER"] if self.hover else COLORS["CARD_BACK"]
            pygame.draw.rect(surface, bg, self.rect, border_radius=12)
            pygame.draw.rect(surface, COLORS["BORDER_DEFAULT"], self.rect, width=2, border_radius=12)

            # Accessible question mark glyph
            q_surf = font_small.render("?", True, COLORS["TEXT_MUTED"])
            q_rect = q_surf.get_rect(center=self.rect.center)
            surface.blit(q_surf, q_rect)


class CognitiveMemoryGame:
    """
    Cognitive Assessment Serious Game with Dynamic Difficulty Adjustment,
    Thread-Safe Multi-Agent Telemetry Ingestion, and Pause/Resume Latency Tracking.
    """
    PAIR_ROUND_GRIDS = ("3x4", "4x4", "4x5", "4x6", "5x6")
    PAIR_ROUND_EXPOSURES = (1.5, 1.35, 1.2, 1.05, 0.9)

    def __init__(
        self,
        headless: bool = False,
        enable_mesa_coupling: bool = True,
        initial_grid: str = "3x4",
        log_filepath: Optional[str] = None
    ):
        self.headless = headless
        self.enable_mesa_coupling = enable_mesa_coupling
        self.grid_size = initial_grid
        self.exposure_time_sec = 1.5

        # Telemetry Logger
        self.logger = TelemetryLogger(log_filepath=log_filepath)

        # Threading & Non-blocking Feedback State
        self._feedback_lock = threading.Lock()
        self._pending_feedback: Optional[Dict[str, Any]] = None
        self._feedback_ready: bool = False
        self.is_analyzing_telemetry: bool = False
        self.pattern_playing = False

        # Mesa Model Integration (if enabled)
        self.mesa_model = None
        if self.enable_mesa_coupling:
            try:
                from simulation.model import CognitiveHealthModel
                self.mesa_model = CognitiveHealthModel(
                    cdr_level=0.0,
                    patient_age=75,
                    target_profile="Elderly",
                    enable_adaptive_dda=True
                )
            except Exception as e:
                print(f"[Warning] Could not initialize Mesa live model: {e}")

        # Game state
        self.round_number = 1
        self.max_pair_rounds = 5
        self.phase = "home"

        self.session_manager = SessionManager()
        self.testing_active = False
        self.testing_games = []
        self.testing_game_index = 0
        self.testing_difficulty = "Easy"
        self.testing_fields = {
            "Participant name": "",
            "Age": "",
            "Previous medical history": "",
            "Gender": "",
        }
        self.testing_field = 0
        self.game_names = ["pairs", "color_pattern", "normal_pattern"]
        self.game_checks = [False, False, False]
        self.session_records = []
        self.selected_session = None

        self.analysis_accuracy_weight = 40
        self.analysis_failure_threshold = 50
        self.analysis_settings_button = pygame.Rect(720, 20, 220, 48)
        self.analysis_accuracy_slider = pygame.Rect(290, 330, 400, 12)
        self.analysis_failure_slider = pygame.Rect(290, 445, 400, 12)

        self.pattern_colors = [
            (235, 45, 45),    # red
            (245, 125, 35),   # orange
            (240, 215, 55),   # yellow
            (45, 190, 75),    # green
            (45, 120, 235),   # blue
            (90, 65, 190),    # indigo
            (175, 65, 190),   # violet
        ]
        self.pattern_color_order = list(range(len(self.pattern_colors)))

        self.pattern_cells = [
            pygame.Rect(135 + col * 180, 230 + row * 135, 150, 110)
            for row, count in ((0, 4), (1, 3))
            for col in range(count)
        ]
        # Center the second row of three tiles.
        for rect in self.pattern_cells[4:]:
            rect.x += 90

        self.normal_pattern_cells = [
            pygame.Rect(330 + col * 105, 190 + row * 105, 90, 90)
            for row in range(3)
            for col in range(3)
        ]
        self.normal_pattern_color = (125, 130, 125)
        self.pattern_click_animations: Dict[int, float] = {}

        # Normal Flashing Pattern: unnumbered, uniform-grey 3×3 grid.
        self.normal_pattern_cells = [
            pygame.Rect(330 + col * 105, 190 + row * 105, 90, 90)
            for row in range(3)
            for col in range(3)
        ]
        self.normal_pattern_color = (125, 130, 125)

        self.cards: List[Card] = []
        self.flipped_cards: List[Card] = []
        self.mismatch_timer: Optional[float] = None
        self.round_completed = False
        self.micro_break_active = False
        self.micro_break_start = 0.0

        # Clinical status banners
        self.last_clinical_flag = "Awaiting First Assessment"
        self.last_predicted_mmse = 30.0
        self.last_dda_reason = "Initial Baseline Round"
        self.difficulty_label = "Gentle / Baseline"

        # Pygame Window Initialization
        self.width = 960
        self.height = 720

        self.pair_menu_button = pygame.Rect(270, 320, 420, 72)
        self.pattern_menu_button = pygame.Rect(270, 420, 420, 72)
        self.normal_pattern_menu_button = pygame.Rect(270, 520, 420, 72)
        self.menu_button = pygame.Rect(20, 20, 150, 48)
        self.home_buttons = [
            pygame.Rect(270, 270, 420, 72),
            pygame.Rect(270, 370, 420, 72),
            pygame.Rect(270, 470, 420, 72),
        ]   
        self.pattern_submit_button = pygame.Rect(390, 570, 180, 52)
        self.pattern_replay_button = pygame.Rect(390, 630, 180, 48)
        self.nav_button = pygame.Rect(350, 430, 260, 58)

        self.screen = None
        self.clock = None

        if not self.headless:
            pygame.init()
            pygame.display.set_caption("22AIE201: Multi-Agent Cognitive Assessment & DDA Serious Game")
            self.screen = pygame.display.set_mode((self.width, self.height))
            self.clock = pygame.time.Clock()

            # Fonts
            self.font_header = pygame.font.SysFont(FONT_FAMILY, FONT_SIZES["HEADER"], bold=True)
            self.font_sub = pygame.font.SysFont(FONT_FAMILY, FONT_SIZES["SUBHEADER"])
            self.font_card = pygame.font.SysFont(FONT_FAMILY, FONT_SIZES["CARD_SYMBOL"], bold=True)
            self.font_metrics = pygame.font.SysFont(FONT_FAMILY, FONT_SIZES["METRICS"])
            self.font_small = pygame.font.SysFont(FONT_FAMILY, 14, bold=True)

        self._setup_round()

    def _setup_round(self):
        """Build the current fixed-sequence difficulty round."""
        if self.phase != "pairs":
            return
        difficulty_index = min(self.round_number - 1, len(self.PAIR_ROUND_GRIDS) - 1)
        self.grid_size = self.PAIR_ROUND_GRIDS[difficulty_index]
        self.exposure_time_sec = self.PAIR_ROUND_EXPOSURES[difficulty_index]

        rows, cols = [int(x) for x in self.grid_size.lower().split("x")]
        total_cards = rows * cols
        total_pairs = total_cards // 2

        # Select symbols using robust fallback generator (never crashes on large boards)
        chosen_symbols = get_symbols_for_pairs(total_pairs)
        symbol_colors = [
            (85, 50, 30), (90, 30, 35), (35, 85, 40), (25, 85, 75),
            (75, 75, 65), (70, 90, 35),
        ]
        pair_items = []
        for pair_id, original_symbol in enumerate(chosen_symbols):
            sym = dict(original_symbol)
            sym["color"] = symbol_colors[pair_id % len(symbol_colors)]
            pair_items.append((pair_id, sym))
            pair_items.append((pair_id, sym))
        random.shuffle(pair_items)

        # Layout parameters
        board_top = 130
        board_bottom = self.height - 110
        board_left = 60
        board_right = self.width - 60
        available_w = board_right - board_left - board_left
        available_h = board_bottom - board_top

        pad_x = 18
        pad_y = 18
        card_w = min(130, int((available_w - (cols - 1) * pad_x) / cols))
        card_h = min(150, int((available_h - (rows - 1) * pad_y) / rows))

        total_grid_w = cols * card_w + (cols - 1) * pad_x
        total_grid_h = rows * card_h + (rows - 1) * pad_y
        start_x = board_left + (available_w - total_grid_w) // 2
        start_y = board_top + (available_h - total_grid_h) // 2

        self.cards.clear()
        self.flipped_cards.clear()
        self.mismatch_timer = None
        self.round_completed = False
        self.is_analyzing_telemetry = False

        idx = 0
        for r in range(rows):
            for c in range(cols):
                rect = pygame.Rect(
                    start_x + c * (card_w + pad_x),
                    start_y + r * (card_h + pad_y),
                    card_w,
                    card_h
                )
                pair_id, sym = pair_items[idx]
                card = Card(idx=idx, pair_id=pair_id, symbol_meta=sym, rect=rect)
                self.cards.append(card)
                idx += 1

        self.logger.start_round(self.round_number, grid_size=self.grid_size, difficulty=self.difficulty_label)

    def handle_click(self, pos: Tuple[int, int]):
        """Processes mouse click on a card with input lock guard."""
        if self.is_analyzing_telemetry or self.round_completed or self.mismatch_timer is not None or self.micro_break_active:
            return

        for card in self.cards:
            if card.rect.collidepoint(pos) and not card.is_flipped and not card.is_matched:
                # Log telemetry
                self.logger.record_card_flip(card.idx, card.symbol_meta["name"])
                card.is_flipped = True
                self.flipped_cards.append(card)

                if len(self.flipped_cards) == 2:
                    c1, c2 = self.flipped_cards
                    is_match = self.logger.record_pair_attempt(
                        c1.idx, c1.pair_id, c2.idx, c2.pair_id
                    )
                    if self.testing_active:
                        self.session_manager.record(
                            "pairs",
                            is_match,
                            round_number=self.round_number,
                            error=None if is_match else "Pair mismatch",
                        )
                    if is_match:
                        c1.is_matched = True
                        c2.is_matched = True
                        self.flipped_cards.clear()
                        # Check victory
                        if all(c.is_matched for c in self.cards):
                            self._on_round_completed()
                    else:
                        # Schedule mismatch flip back and pause latency timer during wait
                        self.mismatch_timer = time.time()
                        self.logger.pause_latency_timer()
                break

    def update(self):
        """Updates game state every frame."""
        now = time.time()

        # Check for async feedback completion from worker thread
        if self._feedback_ready:
            with self._feedback_lock:
                if self._pending_feedback is not None:
                    self._apply_feedback(self._pending_feedback)
                    self._pending_feedback = None
                self._feedback_ready = False

        # Handle micro-break timing
        if self.micro_break_active:
            if now - self.micro_break_start > 5.0:  # 5-second calming restorative break
                self.micro_break_active = False
                self.logger.resume_latency_timer()
                self._setup_round()
            return

        if (
            self.phase in ("home", "testing_form", "testing_config", "sessions",
            "session_detail", "analysis", "results")
            and self.pattern_playing
            and now >= self.pattern_next_at
        ):
            if self.pattern_active_cell is not None:
                self.pattern_active_cell = None
                self.pattern_index += 1
                if self.pattern_index >= len(self.pattern_sequence):
                    self.pattern_playing = False
                    self.pattern_message = "Your turn — repeat the pattern"
                else:
                    self.pattern_next_at = now + 0.25
            else:
                self.pattern_active_cell = self.pattern_sequence[self.pattern_index]
                self.pattern_next_at = now + 0.65
            return

        # Handle flip-back of mismatched cards after exposure delay
        if self.mismatch_timer is not None:
            if now - self.mismatch_timer >= self.exposure_time_sec:
                for c in self.flipped_cards:
                    c.is_flipped = False
                self.flipped_cards.clear()
                self.mismatch_timer = None
                # Resume latency timer when board becomes interactive again
                self.logger.resume_latency_timer()

    def _on_round_completed(self):
        """
        Finalizes round, exports telemetry, and queries Mesa multi-agent loop asynchronously.
        Sets atomic is_analyzing_telemetry lock to eliminate race conditions and frame freezes.
        """
        self.round_completed = True
        self.is_analyzing_telemetry = True
        total_pairs = len(self.cards) // 2
        round_summary = self.logger.complete_round(total_pairs=total_pairs)

        if self.testing_active:
            self.session_manager.record_round_telemetry(
                "pairs",
                self.round_number,
                round_summary,
            )

        if self.mesa_model is not None:
            if self.headless:
                # Synchronous processing in headless/test mode for immediate verification
                feedback = self.mesa_model.process_live_frontend_telemetry(round_summary)
                self._apply_feedback(feedback)
            else:
                # Decoupled worker thread in interactive Pygame mode to maintain 60 FPS
                thread = threading.Thread(
                    target=self._async_process_telemetry,
                    args=(round_summary,),
                    daemon=True
                )
                thread.start()
        else:
            self.is_analyzing_telemetry = False

    def _async_process_telemetry(self, round_summary: Dict[str, Any]):
        """Worker thread executing Mesa agent assessment & DDA decision."""
        try:
            feedback = self.mesa_model.process_live_frontend_telemetry(round_summary)
            with self._feedback_lock:
                self._pending_feedback = feedback
                self._feedback_ready = True
        except Exception as e:
            print(f"[Telemetry Thread Warning] {e}")
            self.is_analyzing_telemetry = False

    def _apply_feedback(self, feedback: Dict[str, Any]):
        """Record Mesa feedback while preserving the fixed five-round schedule."""
        self.last_clinical_flag = feedback.get("clinical_flag", self.last_clinical_flag)
        self.last_predicted_mmse = feedback.get("predicted_mmse", self.last_predicted_mmse)
        self.last_dda_reason = feedback.get("reason", self.last_dda_reason)
        self.difficulty_label = feedback.get("difficulty_name", self.difficulty_label)

        # The board size and exposure are selected by round number in _setup_round.
        if feedback.get("micro_break", False):
            self.micro_break_active = True
            self.micro_break_start = time.time()
            self.logger.pause_latency_timer()

        self.is_analyzing_telemetry = False

    def advance_to_next_round(self):
        """Advances round count and regenerates the board with atomic lock check."""
        if self.is_analyzing_telemetry or not self.round_completed:
            return
        if self.round_number >= self.max_pair_rounds:
            if self.testing_active:
                self._finish_testing_game()
            else:
                self.phase = "pair_complete"
            return
        self.round_number += 1
        self._setup_round()

    def _start_pairs_game(self):
        self.phase = "pairs"
        self.round_number = 1
        self.round_completed = False
        self._setup_round()

    def _pattern_cells_for_phase(self):
        if self.phase == "normal_pattern":
            return self.normal_pattern_cells
        return self.pattern_cells

    @staticmethod
    def _next_pattern_value(sequence, option_count):
        choices = list(range(option_count))
        if len(sequence) >= 2 and sequence[-1] == sequence[-2]:
            choices.remove(sequence[-1])
        return random.choice(choices)

    def _new_pattern_sequence(self, option_count):
        sequence = []
        for _ in range(3):
            sequence.append(self._next_pattern_value(sequence, option_count))
        return sequence

    def _start_pattern_game(self):
        self.phase = "color_pattern"
        self.pattern_level = 1
        random.shuffle(self.pattern_color_order)
        self.pattern_sequence = self._new_pattern_sequence(len(self.pattern_colors))
        self.pattern_click_animations.clear()
        self._replay_pattern()

    def _start_normal_pattern_game(self):
        self.phase = "normal_pattern"
        self.pattern_level = 1
        self.pattern_color_order = list(range(len(self.normal_pattern_cells)))
        self.pattern_sequence = self._new_pattern_sequence(len(self.normal_pattern_cells))
        self.pattern_click_animations.clear()
        self._replay_pattern()

    def _handle_pattern_click(self, pos: Tuple[int, int]):
        if self.pattern_playing:
            return

        for index, rect in enumerate(self._pattern_cells_for_phase()):
            if rect.collidepoint(pos):
                if len(self.pattern_input) < len(self.pattern_sequence):
                    self.pattern_input.append(index)
                    self.pattern_click_animations[index] = time.time()
                    self.pattern_message = (
                        f"Selected {len(self.pattern_input)} of "
                        f"{len(self.pattern_sequence)} — press Enter or Submit"
                    )
                return

    def _submit_pattern(self):
        if self.phase not in ("color_pattern", "normal_pattern") or self.pattern_playing:
            return
        if len(self.pattern_input) != len(self.pattern_sequence):
            self.pattern_message = "Choose the full sequence, then press Enter or Submit"
            return

        if self.pattern_input != self.pattern_sequence:
            if self.testing_active:
                self.session_manager.record(
                    "color_pattern" if self.phase == "color_pattern" else "normal_pattern",
                    False, round_number=self.pattern_level, error="Incorrect pattern",
                )
            self.pattern_message = "Incorrect — watch the pattern again"
            self._replay_pattern()
            return

        if self.testing_active:
            self.session_manager.record(
                "color_pattern" if self.phase == "color_pattern" else "normal_pattern",
                True, round_number=self.pattern_level,
            )

        if self.pattern_level >= self.max_pattern_levels:
            self.pattern_message = f"You completed all {self.max_pattern_levels} levels!"
            if self.testing_active:
                self._finish_testing_game()
            else:
                self.phase = "pattern_complete"
            return

        option_count = (
            len(self.normal_pattern_cells)
            if self.phase == "normal_pattern"
            else len(self.pattern_colors)
        )
        self.pattern_level += 1
        self.pattern_sequence.append(
            self._next_pattern_value(self.pattern_sequence, option_count)
        )
        self._replay_pattern()

    def _draw_glass_button(self, rect, label, font):
        glass = pygame.Surface(rect.size, pygame.SRCALPHA)
        glass.fill((75, 91, 62, 220))
        pygame.draw.rect(
            glass,
            (*COLORS["BORDER_ACTIVE"], 255),
            glass.get_rect(),
            width=2,
            border_radius=14,
        )
        self.screen.blit(glass, rect.topleft)

        text = font.render(label, True, COLORS["TEXT_LIGHT"])
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _replay_pattern(self):
        self.pattern_input.clear()
        self.pattern_index = 0
        self.pattern_active_cell = None
        self.pattern_playing = bool(self.pattern_sequence)
        self.pattern_next_at = time.time() + 0.5
        self.pattern_message = "Watch the pattern"

    def _return_to_menu(self):
        self.phase = "menu"
        self.pattern_playing = False
        self.pattern_active_cell = None
        self.pattern_input.clear()

    def draw(self):
        """Renders the UI."""
        if self.screen is None:
            return

        self.screen.fill(COLORS["BACKGROUND"])

        if self.phase == "menu":
            title = self.font_header.render(
                "Choose a Game", True, COLORS["TEXT_LIGHT"]
            )
            self.screen.blit(title, title.get_rect(center=(self.width // 2, 245)))
            self._draw_glass_button(
                self.pair_menu_button, "Find the Pairs", self.font_sub
            )
            self._draw_glass_button(
                self.pattern_menu_button, "Flashing Pattern Colours", self.font_sub
            )
            self._draw_glass_button(
                self.normal_pattern_menu_button, "Normal Flashing Pattern", self.font_sub
            )
            pygame.display.flip()
            return

        if self.phase in (
            "home", "testing_form", "testing_config", "sessions",
            "session_detail", "analysis", "results"
        ):
            self._draw_section()
            return

        if self.phase in ("color_pattern", "normal_pattern", "pattern_complete"):
            self._draw_glass_button(self.menu_button, "Game Menu", self.font_small)

            cells = (
                self.normal_pattern_cells
                if self.phase == "normal_pattern"
                else self.pattern_cells
            )
            title_text = (
                "Normal Flashing Pattern"
                if self.phase == "normal_pattern"
                else "Flashing Pattern Colours"
            )
            title = self.font_header.render(title_text, True, COLORS["TEXT_LIGHT"])
            self.screen.blit(title, title.get_rect(center=(self.width // 2, 65)))

            status = self.font_sub.render(
                f"Level {self.pattern_level}/10  |  {self.pattern_message}",
                True, COLORS["TEXT_MUTED"]
            )
            self.screen.blit(status, status.get_rect(center=(self.width // 2, 145)))

            now = time.time()
            for index, rect in enumerate(cells):
                active = self.pattern_active_cell == index
                click_started = self.pattern_click_animations.get(index, -1.0)
                elapsed = now - click_started
                pulse = max(0.0, 1.0 - elapsed / 0.30) if elapsed < 0.30 else 0.0

                if self.phase == "normal_pattern":
                    base = self.normal_pattern_color
                    idle = base
                else:
                    mapped_idx = self.pattern_color_order[index]
                    base = self.pattern_colors[mapped_idx]
                    idle = tuple(channel // 3 for channel in base)

                if active:
                    color = (
                        (245, 245, 245)
                        if self.phase == "normal_pattern"
                        else base
                    )
                elif pulse:
                    color = tuple(
                        int(idle[channel] + (255 - idle[channel]) * pulse)
                        for channel in range(3)
                    )
                else:
                    color = idle

                draw_rect = rect.copy()
                if active:
                    draw_rect.inflate_ip(14, 14)
                elif pulse:
                    draw_rect.inflate_ip(int(18 * pulse), int(18 * pulse))

                pygame.draw.rect(self.screen, color, draw_rect, border_radius=16)
                pygame.draw.rect(
                    self.screen, COLORS["BORDER_ACTIVE"],
                    draw_rect, width=3, border_radius=16
                )

                if self.phase == "color_pattern":
                    labels = ("RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "INDIGO", "VIOLET")
                    label = self.font_small.render(
                        labels[self.pattern_color_order[index]], True, COLORS["TEXT_LIGHT"]
                    )
                    self.screen.blit(label, label.get_rect(center=rect.center))

            if self.phase == "pattern_complete":
                complete = self.font_sub.render(
                    "You completed all 10 levels!", True, COLORS["SUCCESS_GREEN"]
                )
                self.screen.blit(complete, complete.get_rect(center=(480, 530)))
            else:
                self._draw_glass_button(
                    self.pattern_submit_button, "Submit (Enter)", self.font_sub
                )
                self._draw_glass_button(
                    self.pattern_replay_button, "Replay", self.font_small
                )

            pygame.display.flip()
            return

        # Bottom Clinical & Agent Telemetry Dashboard
        pygame.draw.rect(self.screen, COLORS["PANEL_BG"], (0, self.height - 95, self.width, 95))
        pygame.draw.line(self.screen, COLORS["BORDER_DEFAULT"], (0, self.height - 95), (self.width, self.height - 95), 2)

        # Screener & DDA Agent Badges
        screener_text = f"Mesa Screener: {self.last_clinical_flag} (MMSE: {self.last_predicted_mmse:.1f}/30)"
        color_flag = COLORS["SUCCESS_GREEN"] if "Normal" in self.last_clinical_flag else (COLORS["ACCENT_GOLD"] if "MCI" in self.last_clinical_flag else COLORS["ERROR_RED"])
        scr_surf = self.font_metrics.render(screener_text, True, color_flag)
        self.screen.blit(scr_surf, (60, self.height - 82))

        dda_text = f"Mesa Adaptive Agent: {self.last_dda_reason}"
        dda_surf = self.font_small.render(dda_text, True, COLORS["TEXT_MUTED"])
        self.screen.blit(dda_surf, (60, self.height - 48))

        # Draw Cards
        mouse_pos = pygame.mouse.get_pos()
        for card in self.cards:
            card.hover = card.rect.collidepoint(mouse_pos)
            card.draw(self.screen, self.font_card, self.font_small)

        # Micro-Break Overlay (Restorative pacing - Mezrar & Bendella, 2022)
        if self.micro_break_active:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((20, 25, 35, 230))
            self.screen.blit(overlay, (0, 0))

            break_title = self.font_header.render("Take a Gentle Breath", True, COLORS["ACCENT_GOLD"])
            break_rect = break_title.get_rect(center=(self.width // 2, self.height // 2 - 30))
            self.screen.blit(break_title, break_rect)

            break_sub = self.font_sub.render("Adaptive Agent detected elevated fatigue. Resuming in a few moments...", True, COLORS["TEXT_LIGHT"])
            break_sub_rect = break_sub.get_rect(center=(self.width // 2, self.height // 2 + 20))
            self.screen.blit(break_sub, break_sub_rect)

        # Round Complete Modal
        elif self.round_completed:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((15, 20, 30, 215))
            self.screen.blit(overlay, (0, 0))

            if self.is_analyzing_telemetry:
                calib_surf = self.font_header.render("Mesa Agents Calibrating Next Round...", True, COLORS["ACCENT_GOLD"])
                calib_rect = calib_surf.get_rect(center=(self.width // 2, self.height // 2 - 25))
                self.screen.blit(calib_surf, calib_rect)

                calib_sub = self.font_sub.render("Processing clinical telemetry & optimizing dynamic difficulty...", True, COLORS["TEXT_LIGHT"])
                sub_rect = calib_sub.get_rect(center=(self.width // 2, self.height // 2 + 25))
                self.screen.blit(calib_sub, sub_rect)
            else:
                win_surf = self.font_header.render("Round Completed!", True, COLORS["SUCCESS_GREEN"])
                win_rect = win_surf.get_rect(center=(self.width // 2, self.height // 2 - 40))
                self.screen.blit(win_surf, win_rect)

                next_label = (
                    "Start Pattern Game"
                    if self.round_number >= self.max_pair_rounds
                    else "Next Round"
                )
                adv_surf = self.font_sub.render(next_label, True, COLORS["TEXT_LIGHT"])
                pygame.draw.rect(self.screen, COLORS["CARD_BACK"], self.nav_button, border_radius=10)
                pygame.draw.rect(self.screen, COLORS["BORDER_ACTIVE"], self.nav_button, 3, border_radius=10)
                self.screen.blit(adv_surf, adv_surf.get_rect(center=self.nav_button.center))
            pygame.display.flip()
            return

        pygame.display.flip()

    def _draw_section(self):
        self.screen.fill(COLORS["BACKGROUND"])

        if self.phase != "home":
            self._draw_glass_button(self.menu_button, "Back", self.font_small)

        if self.phase == "home":
            title = self.font_header.render("Assessment", True, COLORS["TEXT_LIGHT"])
            self.screen.blit(title, title.get_rect(center=(480, 190)))
            for rect, label in zip(
                self.home_buttons, ("Games", "Testing Session", "Sessions")
            ):
                self._draw_glass_button(rect, label, self.font_sub)

        elif self.phase == "testing_form":
            title = self.font_header.render(
                "Participant Details", True, COLORS["TEXT_LIGHT"]
            )
            self.screen.blit(title, title.get_rect(center=(480, 115)))
            for i, (label, value) in enumerate(self.testing_fields.items()):
                rect = pygame.Rect(250, 190 + i * 80, 460, 48)
                pygame.draw.rect(self.screen, COLORS["PANEL_BG"], rect, border_radius=8)
                pygame.draw.rect(
                    self.screen,
                    COLORS["BORDER_ACTIVE"] if i == self.testing_field
                    else COLORS["BORDER_DEFAULT"],
                    rect, 2, border_radius=8,
                )
                text = self.font_small.render(
                    f"{label}: {value}", True, COLORS["TEXT_LIGHT"]
                )
                self.screen.blit(text, (rect.x + 12, rect.y + 15))
            self._draw_glass_button(
                pygame.Rect(390, 540, 180, 55), "Choose Games", self.font_small
            )

        elif self.phase == "testing_config":
            title = self.font_header.render("Testing Setup", True, COLORS["TEXT_LIGHT"])
            self.screen.blit(title, title.get_rect(center=(480, 145)))
            labels = ("Find the Pairs", "Flashing Pattern Colours",
                      "Normal Flashing Pattern")
            for i, (label, y) in enumerate(zip(labels, (220, 275, 330))):
                mark = "[x]" if self.game_checks[i] else "[ ]"
                text = self.font_sub.render(f"{mark}  {label}", True, COLORS["TEXT_LIGHT"])
                self.screen.blit(text, text.get_rect(center=(480, y + 20)))

            for i, difficulty in enumerate(("Easy", "Medium", "Hard")):
                rect = pygame.Rect(190 + i * 200, 430, 180, 55)
                self._draw_glass_button(
                    rect,
                    f"{difficulty} ({ROUNDS_BY_DIFFICULTY[difficulty]})",
                    self.font_small,
                )
                if difficulty == self.testing_difficulty:
                    pygame.draw.rect(
                        self.screen, COLORS["ACCENT_GOLD"], rect, 3, border_radius=14
                    )
            self._draw_glass_button(
                pygame.Rect(390, 540, 180, 55), "Start Test", self.font_small
            )

        elif self.phase == "sessions":
            title = self.font_header.render(
                "Saved Sessions — Results by Game",
                True,
                COLORS["TEXT_LIGHT"],
            )
            self.screen.blit(title, title.get_rect(center=(480, 100)))

            for i, record in enumerate(self.session_records[:5]):
                y = 145 + i * 105
                rect = pygame.Rect(25, y, 910, 96)
                pygame.draw.rect(self.screen, COLORS["PANEL_BG"], rect, border_radius=8)
                pygame.draw.rect(
                    self.screen, COLORS["BORDER_DEFAULT"], rect, 1, border_radius=8
                )

                participant = record.get("participant", {})
                header = self.font_small.render(
                    f'{record.get("timestamp", "")} | '
                    f'{participant.get("name", "Unknown")} | '
                    f'{record.get("status", "")}',
                    True,
                    COLORS["ACCENT_GOLD"],
                )
                self.screen.blit(header, (38, y + 8))

                attempts = record.get("attempts", [])
                for game_index, game_name in enumerate(record.get("allowed_games", [])[:3]):
                    game_attempts = [
                        attempt for attempt in attempts
                        if attempt.get("game") == game_name
                    ]
                    tries = len(game_attempts)
                    successes = sum(
                        1 for attempt in game_attempts
                        if attempt.get("success", False)
                    )
                    rate = successes * 100.0 / tries if tries else 0.0
                    game_line = self.font_small.render(
                        f"{game_name}: Tries {tries} | Successes {successes} | "
                        f"Failures {tries - successes} | Success rate {rate:.1f}%",
                        True,
                        COLORS["TEXT_LIGHT"],
                    )
                    self.screen.blit(game_line, (48, y + 32 + game_index * 20))

        elif self.phase == "session_detail":
            record = self.selected_session
            participant = record.get("participant", {})
            title = self.font_header.render(
                f'{participant.get("name", "Session")} — Telemetry',
                True,
                COLORS["TEXT_LIGHT"],
            )
            self.screen.blit(title, title.get_rect(center=(480, 105)))

            rounds = record.get("rounds", [])
            if not rounds:
                message = self.font_small.render(
                    "No round telemetry saved for this session.",
                    True,
                    COLORS["TEXT_LIGHT"],
                )
                self.screen.blit(message, message.get_rect(center=(480, 190)))
            else:
                for i, item in enumerate(rounds[-8:]):
                    telemetry = item.get("telemetry", {})
                    line1 = (
                        f'{item.get("game", "")} | Round {item.get("round", "")} | '
                        f'Grid: {telemetry.get("Grid_Size", "N/A")} | '
                        f'Pairs: {telemetry.get("Total_Pairs", "N/A")} | '
                        f'Flips: {telemetry.get("Total_Flips", "N/A")}'
                    )
                    line2 = (
                        f'Errors: {telemetry.get("Redundant_Errors", "N/A")} | '
                        f'Error rate: {telemetry.get("Error_Rate", "N/A")} | '
                        f'RT: {telemetry.get("Mean_Reaction_Time_ms", "N/A")} ms | '
                        f'Time: {telemetry.get("Round_Completion_Time_sec", "N/A")} s'
                    )
                    y = 160 + i * 48
                    self.screen.blit(
                        self.font_small.render(line1, True, COLORS["TEXT_LIGHT"]),
                        (35, y),
                    )
                    self.screen.blit(
                        self.font_small.render(line2, True, COLORS["TEXT_LIGHT"]),
                        (35, y + 22),
                    )

        pygame.display.flip()

    def _handle_section_click(self, pos):
        if self.phase == "home":
            for rect, phase in zip(
                self.home_buttons, ("menu", "testing_form", "sessions")
            ):
                if rect.collidepoint(pos):
                    if phase == "sessions":
                        self.session_records = self.session_manager.list_sessions()
                    self.phase = phase
                    return True
            return True

        if self.phase == "menu":
            return False

        if self.phase == "testing_form":
            for i, y in enumerate((190, 270, 350, 430)):
                if pygame.Rect(250, y, 460, 48).collidepoint(pos):
                    self.testing_field = i
                    return True
            if pygame.Rect(390, 540, 180, 55).collidepoint(pos):
                self.phase = "testing_config"
            elif self.menu_button.collidepoint(pos):
                self.phase = "home"
            return True

        if self.phase == "testing_config":
            for i, y in enumerate((220, 275, 330)):
                if pygame.Rect(250, y, 460, 45).collidepoint(pos):
                    self.game_checks[i] = not self.game_checks[i]
                    return True
            for i, difficulty in enumerate(("Easy", "Medium", "Hard")):
                if pygame.Rect(190 + i * 200, 430, 180, 55).collidepoint(pos):
                    self.testing_difficulty = difficulty
                    return True
            if pygame.Rect(390, 540, 180, 55).collidepoint(pos):
                self._start_testing()
            elif self.menu_button.collidepoint(pos):
                self.phase = "testing_form"
            return True

        if self.phase in ("sessions", "results"):
            if self.menu_button.collidepoint(pos):
                self.phase = "home"
                return True
            for i, record in enumerate(self.session_records[:5]):
                if pygame.Rect(25, 145 + i * 105, 910, 96).collidepoint(pos):
                    self.selected_session = record
                    self.phase = "session_detail"
                    return True
            return True

        if self.phase == "session_detail":
            if self.menu_button.collidepoint(pos):
                self.phase = "sessions"
            elif self.analysis_settings_button.collidepoint(pos):
                self.phase = "analysis"
            return True

        if self.phase == "analysis":
            title = self.font_header.render(
                "Analysis Settings", True, COLORS["TEXT_LIGHT"]
            )
            self.screen.blit(title, title.get_rect(center=(480, 110)))

            failure_text = "Failed attempts: unavailable"
            self.screen.blit(
                self.font_sub.render(failure_text, True, COLORS["TEXT_LIGHT"]),
                (150, 175),
            )

            for label, value, slider in (
                ("Accuracy weight", self.analysis_accuracy_weight, self.analysis_accuracy_slider),
                ("Failure review threshold", self.analysis_failure_threshold, self.analysis_failure_slider),
            ):
                self.screen.blit(
                    self.font_small.render(f"{label}: {value}%", True, COLORS["TEXT_LIGHT"]),
                    (150, slider.y - 28),
                )
                pygame.draw.line(
                    self.screen, COLORS["BORDER_DEFAULT"],
                    (slider.left, slider.centery), (slider.right, slider.centery), 6,
                )
                knob_x = slider.left + int(slider.width * value / 100)
                pygame.draw.circle(
                    self.screen, COLORS["ACCENT_GOLD"], (knob_x, slider.centery), 11
                )

            self.screen.blit(
                self.font_small.render(
                    "These settings describe game performance; they do not estimate dementia.",
                    True,
                    COLORS["TEXT_MUTED"],
                ),
                (150, 520),
            )

        pygame.display.flip()

    def _handle_testing_key(self, event):
        if self.phase != "testing_form":
            return False
        field = list(self.testing_fields)[self.testing_field]
        value = self.testing_fields[field]
        if event.key in (pygame.K_TAB, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.testing_field = (self.testing_field + 1) % len(self.testing_fields)
        elif event.key == pygame.K_BACKSPACE:
            self.testing_fields[field] = value[:-1]
        elif event.unicode and event.unicode.isprintable():
            if field != "Age" or event.unicode.isdigit():
                self.testing_fields[field] += event.unicode
        return True

    def _start_testing(self):
        participant = {
            "name": self.testing_fields["Participant name"].strip(),
            "age": self.testing_fields["Age"].strip(),
            "previous_medical_history": self.testing_fields[
                "Previous medical history"
            ].strip(),
            "gender": self.testing_fields["Gender"].strip(),
        }
        if not participant["name"] or not participant["age"].isdigit():
            return

        self.testing_games = [
            name for name, checked in zip(self.game_names, self.game_checks) if checked
        ]
        if not self.testing_games:
            return

        self.session_manager.start(
            participant, self.testing_games, self.testing_difficulty
        )
        if self.mesa_model is not None:
            self.mesa_model.session_id = self.session_manager.data["session_id"]

        self.testing_active = True
        self.testing_game_index = 0
        self._launch_testing_game()

    def _launch_testing_game(self):
        name = self.testing_games[self.testing_game_index]
        rounds = ROUNDS_BY_DIFFICULTY[self.testing_difficulty]
        if name == "pairs":
            self.max_pair_rounds = rounds
            self._start_pairs_game()
        else:
            self.max_pattern_levels = rounds
            if name == "color_pattern":
                self._start_pattern_game()
            else:
                self._start_normal_pattern_game()

    def _finish_testing_game(self):
        self.testing_game_index += 1
        if self.testing_game_index < len(self.testing_games):
            self._launch_testing_game()
        else:
            self.session_manager.finish()
            self.testing_active = False
            self.phase = "results"

    def run(self):
        """Main PyGame event loop."""
        if self.headless:
            print("[Game] Running in headless mode.")
            return

        running = True
        while running:
            self.clock.tick(60)
            self.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._handle_section_click(event.pos):
                        pass
                    elif self.phase == "menu":
                        if self.pair_menu_button.collidepoint(event.pos):
                            if not self.testing_active or "pairs" in self.testing_games:
                                self._start_pairs_game()
                        elif self.pattern_menu_button.collidepoint(event.pos):
                            if not self.testing_active or "color_pattern" in self.testing_games:
                                self._start_pattern_game()
                        elif self.normal_pattern_menu_button.collidepoint(event.pos):
                            if not self.testing_active or "normal_pattern" in self.testing_games:
                                self._start_normal_pattern_game()
                    elif self.phase in ("color_pattern", "normal_pattern", "pattern_complete"):
                        if self.menu_button.collidepoint(event.pos):
                            self._return_to_menu()
                        elif self.phase in ("color_pattern", "normal_pattern"):
                            if self.pattern_submit_button.collidepoint(event.pos):
                                self._submit_pattern()
                            elif self.pattern_replay_button.collidepoint(event.pos):
                                self._replay_pattern()
                            else:
                                self._handle_pattern_click(event.pos)
                    elif self.phase == "pair_complete":
                        if self.menu_button.collidepoint(event.pos):
                            self._return_to_menu()
                    elif self.round_completed and not self.is_analyzing_telemetry:
                        if self.nav_button.collidepoint(event.pos):
                            self.advance_to_next_round()
                    else:
                        self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN and self.phase == "testing_form":
                    self._handle_testing_key(event)
                elif event.type == pygame.KEYDOWN and self.phase in (
                    "color_pattern", "normal_pattern"
                ):
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._submit_pattern()
                    elif event.key == pygame.K_BACKSPACE and not self.pattern_playing:
                        if self.pattern_input:
                            self.pattern_input.pop()
                    elif event.key == pygame.K_ESCAPE:
                        self._return_to_menu()

            self.draw()

        pygame.quit()


if __name__ == "__main__":
    game = CognitiveMemoryGame(headless=False, enable_mesa_coupling=True)
    game.run()
