"""Тема оформления приложения на основе тёмной палитры.

Содержит константы цветов, QSS-стили для всех виджетов и функцию
``apply_theme()``, применяющую QPalette и глобальный stylesheet.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# ── Dark theme tokens ────────────────────────────────────────────────
BG_BASE = "#18181B"
BG_SURFACE = "#1F1F23"
BG_INPUT = "#27272A"
ACCENT = "#6366F1"
ACCENT_HOVER = "#4F46E5"
ACCENT_PRESSED = "#4338CA"
ACCENT_TEXT = "#818CF8"
ACCENT_TINT = "rgba(99, 102, 241, 0.10)"
ACCENT_TINT_STRONG = "rgba(99, 102, 241, 0.18)"
ACCENT_TINT_DROP = "rgba(99, 102, 241, 0.55)"
TEXT_PRIMARY = "#E1E1E6"
TEXT_MUTED = "#A1A1AA"
SUCCESS = "#34D399"
WARNING = "#FBBF24"
WARNING_TINT = "rgba(251, 191, 36, 0.08)"
WARNING_TINT_HOVER = "rgba(251, 191, 36, 0.14)"
ERROR = "#F87171"
STOPPED = "#F97316"
BORDER = "#303036"
BORDER_LIGHT = "#48484F"

# ── Light theme tokens ────────────────────────────────────────────
LIGHT_BG                 = "#FFFFFF"
LIGHT_SURFACE            = "#FAFAFA"
LIGHT_SURFACE_ELEVATED   = "#F4F4F5"
LIGHT_BORDER             = "#E4E4E7"
LIGHT_BORDER_HOVER       = "#D4D4D8"
LIGHT_TEXT_PRIMARY       = "#18181B"
LIGHT_TEXT_SECONDARY     = "#71717A"
LIGHT_TEXT_DISABLED      = "#A1A1AA"
LIGHT_ACCENT             = "#6366F1"
LIGHT_ACCENT_HOVER       = "#4F46E5"
LIGHT_ACCENT_PRESSED     = "#4338CA"
LIGHT_ACCENT_TEXT        = "#4F46E5"
LIGHT_ACCENT_TINT        = "rgba(99, 102, 241, 0.08)"
LIGHT_ACCENT_TINT_STRONG = "rgba(99, 102, 241, 0.15)"
LIGHT_ACCENT_TINT_DROP   = "rgba(99, 102, 241, 0.40)"
LIGHT_SUCCESS            = "#059669"
LIGHT_WARNING            = "#D97706"
LIGHT_WARNING_TINT       = "rgba(217, 119, 6, 0.08)"
LIGHT_WARNING_TINT_HOVER = "rgba(217, 119, 6, 0.14)"
LIGHT_ERROR              = "#DC2626"

DARK_QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QGroupBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 8px 6px 8px;
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}}

QPushButton {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {BORDER_LIGHT};
    border-color: {BORDER_LIGHT};
}}
QPushButton:pressed {{
    background-color: {BORDER};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}

QPushButton#run_btn {{
    background-color: {BG_INPUT};
    color: {ACCENT_TEXT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    font-weight: 600;
}}
QPushButton#run_btn:hover {{
    background-color: {ACCENT_TINT};
    border-color: {ACCENT_HOVER};
}}
QPushButton#run_btn:pressed {{
    background-color: {ACCENT_TINT_STRONG};
}}
QPushButton#run_btn:disabled {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}

QPushButton#stop_btn {{
    background-color: transparent;
    color: {ERROR};
    border: 1px solid {ERROR};
}}
QPushButton#stop_btn:hover {{
    background-color: rgba(239, 68, 68, 0.15);
}}
QPushButton#stop_btn:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit:read-only {{
    color: {TEXT_MUTED};
}}

QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 28px;
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
    border-left: 2px solid {TEXT_MUTED};
    border-bottom: 2px solid {TEXT_MUTED};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_LIGHT};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRIMARY};
    min-height: 18px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QProgressBar[status="done"]::chunk {{
    background-color: {SUCCESS};
}}
QProgressBar[status="error"]::chunk {{
    background-color: {ERROR};
}}
QProgressBar[status="downloading"]::chunk {{
    background-color: {WARNING};
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel#status_label {{
    font-size: 13px;
    padding: 2px 0;
}}
QLabel#status_label[status="success"] {{
    color: {SUCCESS};
}}
QLabel#status_label[status="error"] {{
    color: {ERROR};
}}
QLabel#status_label[status="running"] {{
    color: {TEXT_PRIMARY};
}}
QLabel#muted {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QLabel#screen_title {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QTextBrowser {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    selection-background-color: {ACCENT};
}}

QScrollBar:vertical {{
    background: {BG_SURFACE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {BG_SURFACE};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QDialog {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}
QMessageBox {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}
QFileDialog {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}

QSplitter::handle {{
    background: {BORDER};
    width: 2px;
}}
QSplitter::handle:hover {{
    background: {ACCENT};
}}
QSplitter#editor_splitter::handle {{
    background: {BORDER};
    width: 1px;
}}
QSplitter#editor_splitter::handle:hover {{
    background: {ACCENT};
}}

/* ── Editor header bar ── */

QWidget#editor_header {{
    background-color: {BG_SURFACE};
    border-bottom: 1px solid {BORDER};
    min-height: 52px;
}}

QWidget#editor_footer {{
    background-color: {BG_BASE};
    border-top: 1px solid {BORDER};
    min-height: 40px;
}}

/* ── Navigation sidebar ── */

QWidget#nav_bar {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER};
    min-width: 220px;
    max-width: 220px;
}}

QLabel#nav_title {{
    font-size: 14px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    background-color: {BG_SURFACE};
    border-bottom: 1px solid {BORDER};
    padding: 0 14px;
    min-height: 52px;
}}

QWidget#nav_main_item_row {{
    background-color: {BG_SURFACE};
}}

QPushButton#nav_add_btn {{
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 0;
}}
QPushButton#nav_add_btn:hover {{
    background-color: {BG_INPUT};
}}
QPushButton#nav_add_btn:pressed {{
    background-color: {ACCENT_TINT_STRONG};
}}

QPushButton#nav_main_item {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    border: none;
    border-left: 2px solid transparent;
    border-radius: 6px;
    text-align: left;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 400;
    min-height: 36px;
}}
QPushButton#nav_main_item:hover {{
    background-color: {BG_INPUT};
}}
QPushButton#nav_main_item:checked {{
    background-color: {ACCENT_TINT_STRONG};
    border-left: 2px solid {ACCENT};
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    color: {ACCENT_TEXT};
    font-weight: 500;
}}

QLabel#nav_section {{
    font-size: 10px;
    font-weight: bold;
    color: {TEXT_MUTED};
    background-color: {BG_SURFACE};
    letter-spacing: 1px;
}}

QWidget#nav_list, QWidget#nav_scroll > QWidget > QWidget {{
    background-color: {BG_SURFACE};
}}

QScrollArea#nav_scroll {{
    background-color: {BG_SURFACE};
    border: none;
}}

QFrame#nav_item {{
    background-color: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 6px;
}}
QFrame#nav_item:hover {{
    background-color: {BG_INPUT};
}}
QFrame#nav_item[checked="true"] {{
    background-color: {ACCENT_TINT};
    border-left: 2px solid {ACCENT};
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QLabel#nav_item_name {{
    font-size: 13px;
    font-weight: 400;
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel#nav_item_age {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}
QLabel#nav_status_dot[status="completed"]  {{ background: {SUCCESS};     border-radius: 4px; }}
QLabel#nav_status_dot[status="processing"] {{ background: {ACCENT_TEXT}; border-radius: 4px; }}
QLabel#nav_status_dot[status="stopped"]    {{ background: {TEXT_MUTED};  border-radius: 4px; }}
QLabel#nav_status_dot[status="failed"]     {{ background: {ERROR};       border-radius: 4px; }}
QLabel#nav_status_dot[status="empty"]      {{ background: {BORDER_LIGHT}; border-radius: 4px; }}

/* ── Nav divider ── */

QFrame#nav_divider {{
    background-color: {BORDER};
    border: none;
    margin: 0 12px;
}}

/* ── Processing screen ── */

QTextEdit#proc_log {{
    max-height: 100px;
}}

QProgressBar#download_bar {{
    min-height: 14px;
    max-height: 14px;
}}

/* ── Filter buttons (run history) ── */

QPushButton#filter_btn {{
    background-color: {BG_INPUT};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 12px;
    min-height: 26px;
}}
QPushButton#filter_btn:hover {{
    border-color: {BORDER_LIGHT};
    color: {TEXT_PRIMARY};
}}
QPushButton#filter_btn:checked {{
    background-color: {ACCENT_TINT_STRONG};
    border-color: {ACCENT};
    color: {ACCENT_TEXT};
}}

/* ── Section titles (models screen) ── */

QLabel#section_title {{
    font-size: 13px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    background: transparent;
    padding-bottom: 2px;
    border-bottom: 1px solid {BORDER};
}}

/* ── Run history cards ── */

QFrame#run_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#run_card:hover {{
    border-color: {BORDER_LIGHT};
    background-color: {BG_INPUT};
}}

/* ── Run card labels ── */
QLabel#run_status_icon {{
    min-width: 16px; max-width: 16px;
    font-size: 15px;
    background: transparent;
}}
QLabel#run_status_icon[run_status="completed"] {{ color: {SUCCESS}; }}
QLabel#run_status_icon[run_status="failed"]    {{ color: {ERROR}; }}
QLabel#run_status_icon[run_status="stopped"]   {{ color: {STOPPED}; }}
QLabel#run_status_icon[run_status="running"]   {{ color: {WARNING}; }}
QLabel#run_status_icon[run_status="pending"]   {{ color: {TEXT_MUTED}; }}

QLabel#run_status_text {{
    font-size: 12px;
    background: transparent;
}}
QLabel#run_status_text[run_status="completed"] {{ color: {SUCCESS}; }}
QLabel#run_status_text[run_status="failed"]    {{ color: {ERROR}; }}
QLabel#run_status_text[run_status="stopped"]   {{ color: {STOPPED}; }}
QLabel#run_status_text[run_status="running"]   {{ color: {WARNING}; }}
QLabel#run_status_text[run_status="pending"]   {{ color: {TEXT_MUTED}; }}

QLabel#run_stage_counter {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}
QLabel#run_stages_label {{ font-size: 11px; background: transparent; }}
QLabel#run_empty_title  {{ font-size: 18px; font-weight: bold; background: transparent; }}

/* ── Model cards (legacy) ── */

QFrame#model_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#model_card:hover {{
    border-color: {BORDER_LIGHT};
    background-color: {BG_INPUT};
}}

QLabel#card_status_ok {{
    font-size: 11px;
    color: {SUCCESS};
    background: transparent;
}}

QLabel#card_status_missing {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}

/* ── Model rows (new list view) ── */

QFrame#model_row {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    min-height: 44px;
}}
QFrame#model_row:hover {{
    background-color: {BG_INPUT};
    border-color: {BORDER_LIGHT};
}}

QLabel#model_row_name {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QLabel#model_row_size {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}

/* ── Project cards ── */

QFrame#project_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#project_card:hover {{
    border-color: {BORDER_LIGHT};
    background-color: {BG_INPUT};
}}

QLabel#card_name {{
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

QFrame#drop_zone {{
    border: 2px dashed {BORDER};
    border-radius: 8px;
    background-color: {BG_SURFACE};
}}
QFrame#drop_zone:hover {{
    border-color: {ACCENT};
    background-color: {BG_INPUT};
}}

QFrame#file_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* ── Transcript editor ── */

QWidget#editor_seg_list {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER};
}}

QFrame#seg_item {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    border-left: 2px solid transparent;
}}
QFrame#seg_item:hover {{
    background-color: {BG_INPUT};
}}
QFrame#seg_item[checked="true"] {{
    background-color: {ACCENT_TINT_STRONG};
    border-left: 2px solid {ACCENT};
}}
QLabel#seg_item_header {{
    font-size: 11px;
    background: transparent;
}}
QLabel#seg_item_preview {{
    font-size: 12px;
    color: {TEXT_MUTED};
    background: transparent;
}}

QFrame#editor_panel {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QLabel#dirty_badge {{
    color: {WARNING};
    font-size: 12px;
    background: transparent;
}}

/* ── Pipeline editor ── */

QFrame#stage_tile {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame#stage_tile[tile_state="on"] {{
    border: 2px solid {ACCENT};
    background-color: {ACCENT_TINT};
}}
QFrame#stage_tile[tile_state="off"] {{
    border: 1px solid {BORDER};
    background-color: {BG_SURFACE};
}}
QFrame#stage_tile[tile_state="off"]:hover {{
    border-color: {BORDER_LIGHT};
    background-color: {BG_INPUT};
}}
QFrame#stage_tile[drag_over="true"] {{
    border: 2px solid {ACCENT};
    background-color: {ACCENT_TINT_STRONG};
}}
QFrame#stage_tile[tile_state="warning"] {{
    border: 2px solid {WARNING};
    background-color: {WARNING_TINT};
}}
QFrame#stage_tile[tile_state="warning"]:hover {{
    background-color: {WARNING_TINT_HOVER};
}}
QFrame#stage_tile[tile_state="warning"] QLabel#stage_num {{
    color: {WARNING};
}}

QLabel#stage_card_title {{
    font-size: 15px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QLabel#stage_card_model {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}

QLabel#stage_num {{
    font-size: 11px;
    font-weight: bold;
    color: {TEXT_MUTED};
    background: transparent;
}}
QFrame#stage_tile[tile_state="on"] QLabel#stage_num {{
    color: {ACCENT_TEXT};
}}

QFrame#drop_gap {{
    background: transparent;
    border: none;
    border-radius: 3px;
}}
QFrame#drop_gap[drop_gap_active="true"] {{
    background: {ACCENT_TINT_DROP};
}}

/* ── Port flaps (left/right on StageTile) ── */

QFrame#port_flap_left, QFrame#port_flap_right {{
    background-color: {BORDER_LIGHT};
    border-radius: 2px;
}}
QFrame#port_flap_left[flap_state="ok"] {{
    background-color: {SUCCESS};
}}
QFrame#port_flap_left[flap_state="error"] {{
    background-color: {ERROR};
}}
QFrame#port_flap_left[flap_state="neutral"] {{
    background-color: {BORDER_LIGHT};
}}

/* ── Status bar strips (SmallStageTile bottom) ── */

QFrame#tile_status_bar {{
    background: transparent;
    border: none;
}}
QFrame#tile_bar_in {{
    background-color: {BORDER_LIGHT};
    border-bottom-left-radius: 2px;
}}
QFrame#tile_bar_in[bar_state="ok"] {{
    background-color: {SUCCESS};
}}
QFrame#tile_bar_in[bar_state="error"] {{
    background-color: {ERROR};
}}
QFrame#tile_bar_in[bar_state="neutral"] {{
    background-color: {BORDER_LIGHT};
}}
QFrame#tile_bar_out {{
    background-color: {BORDER_LIGHT};
    border-bottom-right-radius: 2px;
}}

/* ── Pipeline sidebar ── */

QWidget#pipeline_sidebar {{
    background-color: {BG_SURFACE};
    border-left: 1px solid {BORDER};
}}
QWidget#pipeline_sidebar[sidebar_drop_active="true"] {{
    border-left: 2px solid {ACCENT};
    background-color: {ACCENT_TINT};
}}

QFrame#sidebar_bar {{
    background-color: {BG_SURFACE};
    border-bottom: 1px solid {BORDER};
    border-radius: 0;
}}
QFrame#sidebar_bar:hover {{
    background-color: {BG_INPUT};
}}

/* Свёрнутое состояние — выглядит как кнопка */
QFrame#sidebar_bar[bar_collapsed="true"] {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_SURFACE};
}}
QFrame#sidebar_bar[bar_collapsed="true"]:hover {{
    background-color: {BG_INPUT};
    border-color: {TEXT_MUTED};
}}

QLabel#sidebar_title {{
    font-size: 10px;
    font-weight: bold;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
    background: transparent;
}}

QLabel#sidebar_arrow {{
    font-size: 16px;
    font-weight: bold;
    color: {TEXT_MUTED};
    background: transparent;
}}
QFrame#sidebar_bar:hover QLabel#sidebar_arrow {{
    color: {TEXT_PRIMARY};
}}

QLabel#sidebar_stage_item {{
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 4px;
    background: transparent;
    color: {TEXT_MUTED};
}}
QLabel#sidebar_stage_item[item_state="active"] {{
    color: {ACCENT_TEXT};
    background-color: {ACCENT_TINT};
}}
QLabel#sidebar_stage_item[item_state="inactive"] {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel#sidebar_stage_item[item_state="off_board"] {{
    color: {TEXT_MUTED};
    background-color: transparent;
}}
QLabel#sidebar_stage_item[item_state="off_board"]:hover {{
    color: {TEXT_PRIMARY};
    background-color: {BG_INPUT};
}}
QLabel#sidebar_stage_item[item_state="warning"] {{
    color: {WARNING};
    background-color: {WARNING_TINT};
}}

/* ── View toggle (pipeline card zone) ── */

QPushButton#view_toggle_btn {{
    background-color: {BG_INPUT};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
    min-height: 26px;
}}
QPushButton#view_toggle_btn:hover {{
    color: {TEXT_PRIMARY};
    border-color: {BORDER_LIGHT};
}}
QPushButton#view_toggle_btn:checked {{
    background-color: {ACCENT_TINT_STRONG};
    border-color: {ACCENT};
    color: {ACCENT_TEXT};
}}

/* ── Compact stage card title (small tile mode) ── */

QLabel#stage_card_title_sm {{
    font-size: 12px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    background: transparent;
}}

/* ── Transcript editor placeholder ── */

QLabel#editor_placeholder_icon {{
    font-size: 36px;
    background: transparent;
    color: {TEXT_MUTED};
}}
QLabel#editor_placeholder_label {{
    font-size: 16px;
    font-weight: bold;
    background: transparent;
    color: {TEXT_MUTED};
}}

/* ── Speaker rename block ── */

QFrame#editor_spk_frame {{
    background-color: {BG_INPUT};
    border-radius: 6px;
}}

/* ── Audio player transport bar ── */

QWidget#audio_player {{
    background-color: {BG_BASE};
    border-top: 1px solid {BORDER};
    min-height: 44px;
}}
QPushButton#player_btn {{
    padding: 2px 6px;
    min-width: 24px;
    max-height: 28px;
}}
QLabel#player_time {{
    color: {TEXT_MUTED};
    background: transparent;
}}
QSlider#player_seek::groove:horizontal {{
    background: {BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider#player_seek::sub-page:horizontal {{
    background: {ACCENT};
    height: 4px;
    border-radius: 2px;
}}
QSlider#player_seek::handle:horizontal {{
    background: {ACCENT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QPushButton#player_speed_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 0px 6px;
    font-size: 11px;
    min-width: 36px;
    max-height: 22px;
}}
QPushButton#player_speed_btn:hover {{
    border-color: {ACCENT};
    color: {ACCENT_TEXT};
}}
QPushButton#player_speed_btn[active="true"] {{
    border-color: {ACCENT};
    color: {ACCENT_TEXT};
    background-color: {ACCENT_TINT};
}}
QLabel#player_zoom_lbl {{
    color: {TEXT_MUTED};
    font-size: 11px;
    background: transparent;
}}
QSlider#player_zoom::groove:horizontal {{
    background: {BORDER};
    height: 3px;
    border-radius: 1px;
}}
QSlider#player_zoom::sub-page:horizontal {{
    background: {ACCENT};
    height: 3px;
    border-radius: 1px;
}}
QSlider#player_zoom::handle:horizontal {{
    background: {BORDER_LIGHT};
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}}
QSlider#player_zoom::handle:horizontal:hover {{
    background: {ACCENT};
}}

/* ── Preset strip (inline chip row below pipeline editor header) ── */

QWidget#preset_strip {{
    background-color: transparent;
}}

QFrame#preset_chip {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    min-height: 28px;
    max-height: 28px;
}}
QFrame#preset_chip:hover {{
    border-color: {BORDER_LIGHT};
}}
QFrame#preset_chip[chip_state="active"] {{
    background-color: {ACCENT_TINT};
    border: 1px solid {ACCENT};
}}
QFrame#preset_chip[chip_state="saved"] {{
    background-color: {ACCENT_TINT_STRONG};
    border: 1px solid {ACCENT};
}}
QFrame#preset_chip[chip_drop="true"] {{
    border: 2px solid {ACCENT};
    background-color: {ACCENT_TINT};
}}
QFrame#preset_chip QLabel {{
    background: transparent;
    font-size: 12px;
    padding: 0;
}}
QLabel#chip_label {{
    color: {TEXT_MUTED};
}}
QLabel#chip_label[chip_hovered="true"] {{
    color: {TEXT_PRIMARY};
}}
QLabel#chip_label[chip_state="active"] {{
    color: {TEXT_MUTED};
}}
QLabel#chip_label[chip_state="pinned"] {{
    color: {ACCENT_TEXT};
}}
QLabel#chip_label[chip_state="saved"] {{
    color: {ACCENT_TEXT};
}}

QPushButton#preset_chip_del {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: none;
    border-radius: 9999px;
    font-size: 11px;
    padding: 0;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}
QPushButton#preset_chip_del:hover {{
    color: {ERROR};
    background-color: rgba(248, 113, 113, 0.12);
}}

QPushButton#preset_add_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: 1px dashed {BORDER};
    border-radius: 15px;
    font-size: 16px;
    font-weight: 300;
    padding: 0 12px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#preset_add_btn:hover {{
    border-color: {ACCENT};
    color: {ACCENT_TEXT};
}}

/* Иконные кнопки подтверждения/отмены в строке пресетов */
QPushButton#preset_strip_icon_btn {{
    background-color: {BG_INPUT};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-size: 12px;
    padding: 0;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#preset_strip_icon_btn:hover {{
    border-color: {BORDER_LIGHT};
    color: {TEXT_PRIMARY};
}}

/* ── Toast ────────────────────────────────────────────────────────── */
QFrame#toast_item {{
    background-color: {BG_SURFACE};
    border-top:    1px solid {BORDER};
    border-right:  1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    border-left:   3px solid {BORDER};
    border-radius: 8px;
}}
QFrame#toast_item[toast_level="success"] {{ border-left: 3px solid {LIGHT_SUCCESS}; }}
QFrame#toast_item[toast_level="info"]    {{ border-left: 3px solid {ACCENT_PRESSED}; }}
QFrame#toast_item[toast_level="warning"] {{ border-left: 3px solid {LIGHT_WARNING}; }}
QFrame#toast_item[toast_level="error"]   {{ border-left: 3px solid {LIGHT_ERROR}; }}

QLabel#toast_icon {{
    font-size:   13px;
    font-weight: 700;
    background:  transparent;
}}
QLabel#toast_msg {{
    font-size:   13px;
    font-weight: 400;
    background:  transparent;
    color:       {TEXT_PRIMARY};
}}
QPushButton#toast_close_btn {{
    background:    transparent;
    border:        none;
    border-radius: 4px;
    color:         {TEXT_MUTED};
    font-size:     16px;
    font-weight:   400;
    min-width:     20px;
    max-width:     20px;
    min-height:    20px;
    max-height:    20px;
}}
QPushButton#toast_close_btn:hover {{
    background: rgba(255, 255, 255, 0.06);
    color:      {TEXT_PRIMARY};
}}
QPushButton#toast_close_btn:pressed {{
    background: rgba(255, 255, 255, 0.10);
}}

/* ── Theme toggle button ── */
QPushButton#nav_theme_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 6px 10px;
    font-size: 12px;
    min-height: 34px;
    margin: 0 8px;
}}
QPushButton#nav_theme_btn:hover {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
}}

/* ── HuggingFace browser components ── */

QPushButton#hf_browse_btn {{
    background-color: {BG_INPUT};
    color: {ACCENT_TEXT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 14px;
    min-height: 28px;
}}
QPushButton#hf_browse_btn:hover {{
    background-color: {ACCENT_TINT};
    border-color: {ACCENT_HOVER};
}}
QPushButton#hf_browse_btn:pressed {{
    background-color: {ACCENT_TINT_STRONG};
}}

QPushButton#card_download_btn {{
    background-color: transparent;
    color: {ACCENT_TEXT};
    border: 1px solid {ACCENT};
    border-radius: 9999px;
    font-size: 11px;
    padding: 2px 10px;
    min-height: 22px;
}}
QPushButton#card_download_btn:hover {{
    background-color: {ACCENT_TINT};
}}
QPushButton#card_download_btn:pressed {{
    background-color: {ACCENT_TINT_STRONG};
}}
QPushButton#card_download_btn:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}

QFrame#hf_token_bar {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 12px;
}}

QTableWidget#hf_results_table {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {ACCENT_TINT_STRONG};
    selection-color: {ACCENT_TEXT};
    font-size: 12px;
    outline: none;
}}
QTableWidget#hf_results_table::item {{
    padding: 0 8px;
    border-bottom: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
}}
QTableWidget#hf_results_table::item:selected {{
    background-color: {ACCENT_TINT_STRONG};
    color: {ACCENT_TEXT};
}}
QTableWidget#hf_results_table::item:hover {{
    background-color: {BG_INPUT};
}}
QHeaderView#hf_results_table::section {{
    background-color: {BG_SURFACE};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    border-bottom: 1px solid {BORDER};
    border-right: none;
}}
QHeaderView#hf_results_table::section:hover {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
}}
QHeaderView#hf_results_table::section:pressed {{
    background-color: {BORDER};
}}
QHeaderView#hf_results_table::up-arrow {{
    image: none;
    width: 8px; height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {ACCENT};
    margin-right: 4px;
}}
QHeaderView#hf_results_table::down-arrow {{
    image: none;
    width: 8px; height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {ACCENT};
    margin-right: 4px;
}}

QProgressBar#hf_dl_progress {{
    background-color: {BORDER};
    border: none;
    border-radius: 2px;
}}
QProgressBar#hf_dl_progress::chunk {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

QProgressBar#dl_progress {{
    background: rgba(113, 113, 122, 0.15);
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {ACCENT_TEXT};
    font-size: 11px;
    font-weight: 600;
}}
QProgressBar#dl_progress::chunk {{
    background: rgba(99, 102, 241, 0.55);
    border-radius: 3px;
}}

/* ── Model status chips ── */

QLabel#chip_none {{
    background: rgba(113, 113, 122, 0.15);
    color: {TEXT_MUTED};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_loading {{
    background: rgba(99, 102, 241, 0.15);
    color: {ACCENT_TEXT};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_ready {{
    background: rgba(52, 211, 153, 0.15);
    color: {SUCCESS};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_error {{
    background: rgba(248, 113, 113, 0.15);
    color: {ERROR};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton#chip_cancel_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 9999px;
    font-size: 11px;
    padding: 2px 10px;
    min-height: 22px;
}}
QPushButton#chip_cancel_btn:hover {{
    color: {ERROR};
    border-color: {ERROR};
    background-color: rgba(248, 113, 113, 0.08);
}}

QLabel#pipeline_dirty_label {{
    color: {WARNING};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}

/* ── HF Token contextual banner ── */

QFrame#token_banner {{
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.25);
    border-radius: 6px;
}}

/* ── Model meta-tags ── */

QLabel#speed_fast {{
    background: rgba(52, 211, 153, 0.10);
    color: {SUCCESS};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#speed_medium {{
    background: rgba(251, 191, 36, 0.10);
    color: {WARNING};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#speed_slow {{
    background: rgba(248, 113, 113, 0.10);
    color: {ERROR};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#lang_tag {{
    background: rgba(113, 113, 122, 0.12);
    color: {TEXT_MUTED};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#recommended_badge {{
    background: rgba(99, 102, 241, 0.15);
    color: {ACCENT_TEXT};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
}}

/* ── Custom model badges ── */

QLabel#custom_badge {{
    background: rgba(251, 191, 36, 0.12);
    color: {WARNING};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QPushButton#custom_del_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: none;
    border-radius: 9999px;
    font-size: 11px;
    padding: 0;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}
QPushButton#custom_del_btn:hover {{
    color: {ERROR};
    background-color: rgba(248, 113, 113, 0.12);
}}

/* ── Processing screen progress bars ── */

QProgressBar#stage_bar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRIMARY};
    min-height: 8px;
    max-height: 8px;
    font-size: 10px;
}}
QProgressBar#stage_bar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QProgressBar#stage_bar[status="done"]::chunk {{
    background-color: {SUCCESS};
}}
QProgressBar#stage_bar[status="error"]::chunk {{
    background-color: {ERROR};
}}

QProgressBar#seg_bar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRIMARY};
    min-height: 20px;
    max-height: 20px;
    font-size: 12px;
}}
QProgressBar#seg_bar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

/* ── Stage timeline pills ── */
QLabel#stage_pill {{
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    color: {TEXT_MUTED};
    background: transparent;
}}
QLabel#stage_pill[stage_state="active"] {{
    color: {TEXT_PRIMARY};
    font-weight: bold;
}}
QLabel#stage_pill[stage_state="done"] {{
    color: {SUCCESS};
}}
QLabel#stage_pill[stage_state="error"] {{
    color: {ERROR};
}}
QLabel#stage_sep {{
    color: {TEXT_MUTED};
    font-size: 10px;
    background: transparent;
}}

/* ── Model download label ── */
QLabel#proc_download_label {{
    font-size: 12px;
    color: {WARNING};
    background: transparent;
    padding: 2px 0;
}}

/* ── Tooltip ── */

QToolTip {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""

LIGHT_QSS = f"""
QMainWindow, QWidget {{
    background-color: {LIGHT_BG};
    color: {LIGHT_TEXT_PRIMARY};
    font-size: 13px;
}}

QGroupBox {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 8px 6px 8px;
    font-size: 12px;
    color: {LIGHT_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}}

QPushButton {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {LIGHT_BORDER_HOVER};
    border-color: {LIGHT_BORDER_HOVER};
}}
QPushButton:pressed {{
    background-color: {LIGHT_BORDER};
}}
QPushButton:disabled {{
    color: {LIGHT_TEXT_DISABLED};
    border-color: {LIGHT_BORDER};
}}

QPushButton#run_btn {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_ACCENT_TEXT};
    border: 1px solid {LIGHT_ACCENT};
    border-radius: 4px;
    font-weight: 600;
}}
QPushButton#run_btn:hover {{
    background-color: {LIGHT_ACCENT_TINT};
    border-color: {LIGHT_ACCENT_HOVER};
}}
QPushButton#run_btn:pressed {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
}}
QPushButton#run_btn:disabled {{
    background-color: transparent;
    color: {LIGHT_TEXT_DISABLED};
    border-color: {LIGHT_BORDER};
}}

QPushButton#stop_btn {{
    background-color: transparent;
    color: {LIGHT_ERROR};
    border: 1px solid {LIGHT_ERROR};
}}
QPushButton#stop_btn:hover {{
    background-color: rgba(220, 38, 38, 0.10);
}}
QPushButton#stop_btn:disabled {{
    color: {LIGHT_TEXT_SECONDARY};
    border-color: {LIGHT_BORDER};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {LIGHT_ACCENT};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {LIGHT_ACCENT};
}}
QLineEdit:read-only {{
    color: {LIGHT_TEXT_SECONDARY};
}}

QComboBox {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 28px;
}}
QComboBox:focus {{
    border-color: {LIGHT_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
    border-left: 2px solid {LIGHT_TEXT_SECONDARY};
    border-bottom: 2px solid {LIGHT_TEXT_SECONDARY};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    selection-background-color: {LIGHT_ACCENT};
}}

QCheckBox {{
    color: {LIGHT_TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {LIGHT_BORDER_HOVER};
    border-radius: 3px;
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QCheckBox::indicator:checked {{
    background-color: {LIGHT_ACCENT};
    border-color: {LIGHT_ACCENT};
}}

QProgressBar {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {LIGHT_TEXT_PRIMARY};
    min-height: 18px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {LIGHT_ACCENT};
    border-radius: 3px;
}}
QProgressBar[status="done"]::chunk {{
    background-color: {LIGHT_SUCCESS};
}}
QProgressBar[status="error"]::chunk {{
    background-color: {LIGHT_ERROR};
}}
QProgressBar[status="downloading"]::chunk {{
    background-color: {LIGHT_WARNING};
}}

QLabel {{
    color: {LIGHT_TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel#status_label {{
    font-size: 13px;
    padding: 2px 0;
}}
QLabel#status_label[status="success"] {{
    color: {LIGHT_SUCCESS};
}}
QLabel#status_label[status="error"] {{
    color: {LIGHT_ERROR};
}}
QLabel#status_label[status="running"] {{
    color: {LIGHT_TEXT_PRIMARY};
}}
QLabel#muted {{
    color: {LIGHT_TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel#screen_title {{
    font-size: 18px;
    font-weight: 700;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
}}

QTextBrowser {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 8px;
    selection-background-color: {LIGHT_ACCENT};
}}

QScrollBar:vertical {{
    background: {LIGHT_SURFACE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {LIGHT_BORDER_HOVER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {LIGHT_TEXT_SECONDARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {LIGHT_SURFACE};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {LIGHT_BORDER_HOVER};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {LIGHT_TEXT_SECONDARY};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QDialog {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT_PRIMARY};
}}
QMessageBox {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT_PRIMARY};
}}
QFileDialog {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT_PRIMARY};
}}

QSplitter::handle {{
    background: {LIGHT_BORDER};
    width: 2px;
}}
QSplitter::handle:hover {{
    background: {LIGHT_ACCENT};
}}
QSplitter#editor_splitter::handle {{
    background: {LIGHT_BORDER};
    width: 1px;
}}
QSplitter#editor_splitter::handle:hover {{
    background: {LIGHT_ACCENT};
}}

/* ── Editor header bar ── */

QWidget#editor_header {{
    background-color: {LIGHT_SURFACE};
    border-bottom: 1px solid {LIGHT_BORDER};
    min-height: 52px;
}}

QWidget#editor_footer {{
    background-color: {LIGHT_BG};
    border-top: 1px solid {LIGHT_BORDER};
    min-height: 40px;
}}

/* ── Navigation sidebar ── */

QWidget#nav_bar {{
    background-color: {LIGHT_SURFACE};
    border-right: 1px solid {LIGHT_BORDER};
    min-width: 220px;
    max-width: 220px;
}}

QLabel#nav_title {{
    font-size: 14px;
    font-weight: bold;
    color: {LIGHT_TEXT_PRIMARY};
    background-color: {LIGHT_SURFACE};
    border-bottom: 1px solid {LIGHT_BORDER};
    padding: 0 14px;
    min-height: 52px;
}}

QWidget#nav_main_item_row {{
    background-color: {LIGHT_SURFACE};
}}

QPushButton#nav_add_btn {{
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 0;
}}
QPushButton#nav_add_btn:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QPushButton#nav_add_btn:pressed {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
}}

QPushButton#nav_main_item {{
    background-color: transparent;
    color: {LIGHT_TEXT_PRIMARY};
    border: none;
    border-left: 2px solid transparent;
    border-radius: 6px;
    text-align: left;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 400;
    min-height: 36px;
}}
QPushButton#nav_main_item:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QPushButton#nav_main_item:checked {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    border-left: 2px solid {LIGHT_ACCENT};
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    color: {LIGHT_ACCENT_TEXT};
    font-weight: 500;
}}

QLabel#nav_section {{
    font-size: 10px;
    font-weight: bold;
    color: {LIGHT_TEXT_SECONDARY};
    background-color: {LIGHT_SURFACE};
    letter-spacing: 1px;
}}

QWidget#nav_list, QWidget#nav_scroll > QWidget > QWidget {{
    background-color: {LIGHT_SURFACE};
}}

QScrollArea#nav_scroll {{
    background-color: {LIGHT_SURFACE};
    border: none;
}}

QFrame#nav_item {{
    background-color: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 6px;
}}
QFrame#nav_item:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QFrame#nav_item[checked="true"] {{
    background-color: {LIGHT_ACCENT_TINT};
    border-left: 2px solid {LIGHT_ACCENT};
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QLabel#nav_item_name {{
    font-size: 13px;
    font-weight: 400;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
}}
QLabel#nav_item_age {{
    font-size: 11px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}
QLabel#nav_status_dot[status="completed"]  {{ background: {LIGHT_SUCCESS};       border-radius: 4px; }}
QLabel#nav_status_dot[status="processing"] {{ background: {LIGHT_ACCENT_TEXT};   border-radius: 4px; }}
QLabel#nav_status_dot[status="stopped"]    {{ background: {LIGHT_TEXT_SECONDARY}; border-radius: 4px; }}
QLabel#nav_status_dot[status="failed"]     {{ background: {LIGHT_ERROR};         border-radius: 4px; }}
QLabel#nav_status_dot[status="empty"]      {{ background: {LIGHT_BORDER_HOVER};  border-radius: 4px; }}

/* ── Nav divider ── */

QFrame#nav_divider {{
    background-color: {LIGHT_BORDER};
    border: none;
    margin: 0 12px;
}}

/* ── Processing screen ── */

QTextEdit#proc_log {{
    max-height: 100px;
}}

QProgressBar#download_bar {{
    min-height: 14px;
    max-height: 14px;
}}

/* ── Filter buttons (run history) ── */

QPushButton#filter_btn {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 12px;
    min-height: 26px;
}}
QPushButton#filter_btn:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    color: {LIGHT_TEXT_PRIMARY};
}}
QPushButton#filter_btn:checked {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    border-color: {LIGHT_ACCENT};
    color: {LIGHT_ACCENT_TEXT};
}}

/* ── Section titles (models screen) ── */

QLabel#section_title {{
    font-size: 13px;
    font-weight: bold;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
    padding-bottom: 2px;
    border-bottom: 1px solid {LIGHT_BORDER};
}}

/* ── Run history cards ── */

QFrame#run_card {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}
QFrame#run_card:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}

/* ── Run card labels ── */
QLabel#run_status_icon {{
    min-width: 16px; max-width: 16px;
    font-size: 15px;
    background: transparent;
}}
QLabel#run_status_icon[run_status="completed"] {{ color: {LIGHT_SUCCESS}; }}
QLabel#run_status_icon[run_status="failed"]    {{ color: {LIGHT_ERROR}; }}
QLabel#run_status_icon[run_status="stopped"]   {{ color: {STOPPED}; }}
QLabel#run_status_icon[run_status="running"]   {{ color: {LIGHT_WARNING}; }}
QLabel#run_status_icon[run_status="pending"]   {{ color: {TEXT_MUTED}; }}

QLabel#run_status_text {{
    font-size: 12px;
    background: transparent;
}}
QLabel#run_status_text[run_status="completed"] {{ color: {LIGHT_SUCCESS}; }}
QLabel#run_status_text[run_status="failed"]    {{ color: {LIGHT_ERROR}; }}
QLabel#run_status_text[run_status="stopped"]   {{ color: {STOPPED}; }}
QLabel#run_status_text[run_status="running"]   {{ color: {LIGHT_WARNING}; }}
QLabel#run_status_text[run_status="pending"]   {{ color: {TEXT_MUTED}; }}

QLabel#run_stage_counter {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: transparent;
}}
QLabel#run_stages_label {{ font-size: 11px; background: transparent; }}
QLabel#run_empty_title  {{ font-size: 18px; font-weight: bold; background: transparent; }}

/* ── Model cards (legacy) ── */

QFrame#model_card {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}
QFrame#model_card:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}

QLabel#card_status_ok {{
    font-size: 11px;
    color: {LIGHT_SUCCESS};
    background: transparent;
}}

QLabel#card_status_missing {{
    font-size: 11px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}

/* ── Model rows (new list view) ── */

QFrame#model_row {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 6px;
    min-height: 44px;
}}
QFrame#model_row:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border-color: {LIGHT_BORDER_HOVER};
}}

QLabel#model_row_name {{
    font-size: 13px;
    font-weight: 600;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
}}

QLabel#model_row_size {{
    font-size: 11px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}

/* ── Project cards ── */

QFrame#project_card {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}
QFrame#project_card:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}

QLabel#card_name {{
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

QFrame#drop_zone {{
    border: 2px dashed {LIGHT_BORDER};
    border-radius: 8px;
    background-color: {LIGHT_SURFACE};
}}
QFrame#drop_zone:hover {{
    border-color: {LIGHT_ACCENT};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}

QFrame#file_card {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}

/* ── Transcript editor ── */

QWidget#editor_seg_list {{
    background-color: {LIGHT_SURFACE};
    border-right: 1px solid {LIGHT_BORDER};
}}

QFrame#seg_item {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    border-left: 2px solid transparent;
}}
QFrame#seg_item:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QFrame#seg_item[checked="true"] {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    border-left: 2px solid {LIGHT_ACCENT};
}}
QLabel#seg_item_header {{
    font-size: 11px;
    background: transparent;
}}
QLabel#seg_item_preview {{
    font-size: 12px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}

QFrame#editor_panel {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}

QLabel#dirty_badge {{
    color: {LIGHT_WARNING};
    font-size: 12px;
    background: transparent;
}}

/* ── Pipeline editor ── */

QFrame#stage_tile {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 6px;
}}
QFrame#stage_tile[tile_state="on"] {{
    border: 2px solid {LIGHT_ACCENT};
    background-color: {LIGHT_ACCENT_TINT};
}}
QFrame#stage_tile[tile_state="off"] {{
    border: 1px solid {LIGHT_BORDER};
    background-color: {LIGHT_SURFACE};
}}
QFrame#stage_tile[tile_state="off"]:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QFrame#stage_tile[drag_over="true"] {{
    border: 2px solid {LIGHT_ACCENT};
    background-color: {LIGHT_ACCENT_TINT_STRONG};
}}
QFrame#stage_tile[tile_state="warning"] {{
    border: 2px solid {LIGHT_WARNING};
    background-color: {LIGHT_WARNING_TINT};
}}
QFrame#stage_tile[tile_state="warning"]:hover {{
    background-color: {LIGHT_WARNING_TINT_HOVER};
}}
QFrame#stage_tile[tile_state="warning"] QLabel#stage_num {{
    color: {LIGHT_WARNING};
}}

QLabel#stage_card_title {{
    font-size: 15px;
    font-weight: bold;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
}}

QLabel#stage_card_model {{
    font-size: 11px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}

QLabel#stage_num {{
    font-size: 11px;
    font-weight: bold;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}
QFrame#stage_tile[tile_state="on"] QLabel#stage_num {{
    color: {LIGHT_ACCENT_TEXT};
}}

QFrame#drop_gap {{
    background: transparent;
    border: none;
    border-radius: 3px;
}}
QFrame#drop_gap[drop_gap_active="true"] {{
    background: {LIGHT_ACCENT_TINT_DROP};
}}

/* ── Port flaps (left/right on StageTile) ── */

QFrame#port_flap_left, QFrame#port_flap_right {{
    background-color: {LIGHT_BORDER_HOVER};
    border-radius: 2px;
}}
QFrame#port_flap_left[flap_state="ok"] {{
    background-color: {LIGHT_SUCCESS};
}}
QFrame#port_flap_left[flap_state="error"] {{
    background-color: {LIGHT_ERROR};
}}
QFrame#port_flap_left[flap_state="neutral"] {{
    background-color: {LIGHT_BORDER_HOVER};
}}

/* ── Status bar strips (SmallStageTile bottom) ── */

QFrame#tile_status_bar {{
    background: transparent;
    border: none;
}}
QFrame#tile_bar_in {{
    background-color: {LIGHT_BORDER_HOVER};
    border-bottom-left-radius: 2px;
}}
QFrame#tile_bar_in[bar_state="ok"] {{
    background-color: {LIGHT_SUCCESS};
}}
QFrame#tile_bar_in[bar_state="error"] {{
    background-color: {LIGHT_ERROR};
}}
QFrame#tile_bar_in[bar_state="neutral"] {{
    background-color: {LIGHT_BORDER_HOVER};
}}
QFrame#tile_bar_out {{
    background-color: {LIGHT_BORDER_HOVER};
    border-bottom-right-radius: 2px;
}}

/* ── Pipeline sidebar ── */

QWidget#pipeline_sidebar {{
    background-color: {LIGHT_SURFACE};
    border-left: 1px solid {LIGHT_BORDER};
}}
QWidget#pipeline_sidebar[sidebar_drop_active="true"] {{
    border-left: 2px solid {LIGHT_ACCENT};
    background-color: {LIGHT_ACCENT_TINT};
}}

QFrame#sidebar_bar {{
    background-color: {LIGHT_SURFACE};
    border-bottom: 1px solid {LIGHT_BORDER};
    border-radius: 0;
}}
QFrame#sidebar_bar:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}

QFrame#sidebar_bar[bar_collapsed="true"] {{
    border: 1px solid {LIGHT_BORDER};
    border-radius: 6px;
    background-color: {LIGHT_SURFACE};
}}
QFrame#sidebar_bar[bar_collapsed="true"]:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border-color: {LIGHT_TEXT_SECONDARY};
}}

QLabel#sidebar_title {{
    font-size: 10px;
    font-weight: bold;
    color: {LIGHT_TEXT_SECONDARY};
    letter-spacing: 1px;
    background: transparent;
}}

QLabel#sidebar_arrow {{
    font-size: 16px;
    font-weight: bold;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}
QFrame#sidebar_bar:hover QLabel#sidebar_arrow {{
    color: {LIGHT_TEXT_PRIMARY};
}}

QLabel#sidebar_stage_item {{
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 4px;
    background: transparent;
    color: {LIGHT_TEXT_SECONDARY};
}}
QLabel#sidebar_stage_item[item_state="active"] {{
    color: {LIGHT_ACCENT_TEXT};
    background-color: {LIGHT_ACCENT_TINT};
}}
QLabel#sidebar_stage_item[item_state="inactive"] {{
    color: {LIGHT_TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel#sidebar_stage_item[item_state="off_board"] {{
    color: {LIGHT_TEXT_SECONDARY};
    background-color: transparent;
}}
QLabel#sidebar_stage_item[item_state="off_board"]:hover {{
    color: {LIGHT_TEXT_PRIMARY};
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QLabel#sidebar_stage_item[item_state="warning"] {{
    color: {LIGHT_WARNING};
    background-color: {LIGHT_WARNING_TINT};
}}

/* ── View toggle (pipeline card zone) ── */

QPushButton#view_toggle_btn {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
    min-height: 26px;
}}
QPushButton#view_toggle_btn:hover {{
    color: {LIGHT_TEXT_PRIMARY};
    border-color: {LIGHT_BORDER_HOVER};
}}
QPushButton#view_toggle_btn:checked {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    border-color: {LIGHT_ACCENT};
    color: {LIGHT_ACCENT_TEXT};
}}

/* ── Compact stage card title (small tile mode) ── */

QLabel#stage_card_title_sm {{
    font-size: 12px;
    font-weight: bold;
    color: {LIGHT_TEXT_PRIMARY};
    background: transparent;
}}

/* ── Transcript editor placeholder ── */

QLabel#editor_placeholder_icon {{
    font-size: 36px;
    background: transparent;
    color: {LIGHT_TEXT_SECONDARY};
}}
QLabel#editor_placeholder_label {{
    font-size: 16px;
    font-weight: bold;
    background: transparent;
    color: {LIGHT_TEXT_SECONDARY};
}}

/* ── Speaker rename block ── */

QFrame#editor_spk_frame {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border-radius: 6px;
}}

/* ── Audio player transport bar ── */

QWidget#audio_player {{
    background-color: {LIGHT_BG};
    border-top: 1px solid {LIGHT_BORDER};
    min-height: 44px;
}}
QPushButton#player_btn {{
    padding: 2px 6px;
    min-width: 24px;
    max-height: 28px;
}}
QLabel#player_time {{
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}
QSlider#player_seek::groove:horizontal {{
    background: {LIGHT_BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider#player_seek::sub-page:horizontal {{
    background: {LIGHT_ACCENT};
    height: 4px;
    border-radius: 2px;
}}
QSlider#player_seek::handle:horizontal {{
    background: {LIGHT_ACCENT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QPushButton#player_speed_btn {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 3px;
    padding: 0px 6px;
    font-size: 11px;
    min-width: 36px;
    max-height: 22px;
}}
QPushButton#player_speed_btn:hover {{
    border-color: {LIGHT_ACCENT};
    color: {LIGHT_ACCENT_TEXT};
}}
QPushButton#player_speed_btn[active="true"] {{
    border-color: {LIGHT_ACCENT};
    color: {LIGHT_ACCENT_TEXT};
    background-color: {LIGHT_ACCENT_TINT};
}}
QLabel#player_zoom_lbl {{
    color: {LIGHT_TEXT_SECONDARY};
    font-size: 11px;
    background: transparent;
}}
QSlider#player_zoom::groove:horizontal {{
    background: {LIGHT_BORDER};
    height: 3px;
    border-radius: 1px;
}}
QSlider#player_zoom::sub-page:horizontal {{
    background: {LIGHT_ACCENT};
    height: 3px;
    border-radius: 1px;
}}
QSlider#player_zoom::handle:horizontal {{
    background: {LIGHT_BORDER_HOVER};
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}}
QSlider#player_zoom::handle:horizontal:hover {{
    background: {LIGHT_ACCENT};
}}

/* ── Preset strip (inline chip row below pipeline editor header) ── */

QWidget#preset_strip {{
    background-color: transparent;
}}

QFrame#preset_chip {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    min-height: 28px;
    max-height: 28px;
}}
QFrame#preset_chip:hover {{
    border-color: {LIGHT_BORDER_HOVER};
}}
QFrame#preset_chip[chip_state="active"] {{
    background-color: {LIGHT_ACCENT_TINT};
    border: 1px solid {LIGHT_ACCENT};
}}
QFrame#preset_chip[chip_state="saved"] {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    border: 1px solid {LIGHT_ACCENT};
}}
QFrame#preset_chip[chip_drop="true"] {{
    border: 2px solid {LIGHT_ACCENT};
    background-color: {LIGHT_ACCENT_TINT};
}}
QFrame#preset_chip QLabel {{
    background: transparent;
    font-size: 12px;
    padding: 0;
}}
QLabel#chip_label {{
    color: {LIGHT_TEXT_SECONDARY};
}}
QLabel#chip_label[chip_hovered="true"] {{
    color: {LIGHT_TEXT_PRIMARY};
}}
QLabel#chip_label[chip_state="active"] {{
    color: {LIGHT_TEXT_SECONDARY};
}}
QLabel#chip_label[chip_state="pinned"] {{
    color: {LIGHT_ACCENT_TEXT};
}}
QLabel#chip_label[chip_state="saved"] {{
    color: {LIGHT_ACCENT_TEXT};
}}

QPushButton#preset_chip_del {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: none;
    border-radius: 9999px;
    font-size: 11px;
    padding: 0;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}
QPushButton#preset_chip_del:hover {{
    color: {LIGHT_ERROR};
    background-color: rgba(220, 38, 38, 0.10);
}}

QPushButton#preset_add_btn {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px dashed {LIGHT_BORDER};
    border-radius: 15px;
    font-size: 16px;
    font-weight: 300;
    padding: 0 12px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#preset_add_btn:hover {{
    border-color: {LIGHT_ACCENT};
    color: {LIGHT_ACCENT_TEXT};
}}

QPushButton#preset_strip_icon_btn {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    font-size: 12px;
    padding: 0;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#preset_strip_icon_btn:hover {{
    border-color: {LIGHT_BORDER_HOVER};
    color: {LIGHT_TEXT_PRIMARY};
}}

/* ── Toast ────────────────────────────────────────────────────────── */
QFrame#toast_item {{
    background-color: {LIGHT_SURFACE};
    border-top:    1px solid {LIGHT_BORDER};
    border-right:  1px solid {LIGHT_BORDER};
    border-bottom: 1px solid {LIGHT_BORDER};
    border-left:   3px solid {LIGHT_BORDER};
    border-radius: 8px;
}}
QFrame#toast_item[toast_level="success"] {{ border-left: 3px solid {LIGHT_SUCCESS}; }}
QFrame#toast_item[toast_level="info"]    {{ border-left: 3px solid {LIGHT_ACCENT_PRESSED}; }}
QFrame#toast_item[toast_level="warning"] {{ border-left: 3px solid {LIGHT_WARNING}; }}
QFrame#toast_item[toast_level="error"]   {{ border-left: 3px solid {LIGHT_ERROR}; }}

QLabel#toast_icon {{
    font-size:   13px;
    font-weight: 700;
    background:  transparent;
}}
QLabel#toast_msg {{
    font-size:   13px;
    font-weight: 400;
    background:  transparent;
    color:       {LIGHT_TEXT_PRIMARY};
}}
QPushButton#toast_close_btn {{
    background:    transparent;
    border:        none;
    border-radius: 4px;
    color:         {LIGHT_TEXT_SECONDARY};
    font-size:     16px;
    font-weight:   400;
    min-width:     20px;
    max-width:     20px;
    min-height:    20px;
    max-height:    20px;
}}
QPushButton#toast_close_btn:hover {{
    background: rgba(0, 0, 0, 0.05);
    color:      {LIGHT_TEXT_PRIMARY};
}}
QPushButton#toast_close_btn:pressed {{
    background: rgba(0, 0, 0, 0.08);
}}

/* ── Theme toggle button ── */
QPushButton#nav_theme_btn {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 6px 10px;
    font-size: 12px;
    min-height: 34px;
    margin: 0 8px;
}}
QPushButton#nav_theme_btn:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
}}

/* ── HuggingFace browser components ── */

QPushButton#hf_browse_btn {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_ACCENT_TEXT};
    border: 1px solid {LIGHT_ACCENT};
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 14px;
    min-height: 28px;
}}
QPushButton#hf_browse_btn:hover {{
    background-color: {LIGHT_ACCENT_TINT};
    border-color: {LIGHT_ACCENT_HOVER};
}}
QPushButton#hf_browse_btn:pressed {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
}}

QPushButton#card_download_btn {{
    background-color: transparent;
    color: {LIGHT_ACCENT_TEXT};
    border: 1px solid {LIGHT_ACCENT};
    border-radius: 9999px;
    font-size: 11px;
    padding: 2px 10px;
    min-height: 22px;
}}
QPushButton#card_download_btn:hover {{
    background-color: {LIGHT_ACCENT_TINT};
}}
QPushButton#card_download_btn:pressed {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
}}
QPushButton#card_download_btn:disabled {{
    color: {LIGHT_TEXT_SECONDARY};
    border-color: {LIGHT_BORDER};
}}

QFrame#hf_token_bar {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    padding: 6px 12px;
}}

QTableWidget#hf_results_table {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {LIGHT_ACCENT_TINT_STRONG};
    selection-color: {LIGHT_ACCENT_TEXT};
    font-size: 12px;
    outline: none;
}}
QTableWidget#hf_results_table::item {{
    padding: 0 8px;
    border-bottom: 1px solid {LIGHT_BORDER};
    color: {LIGHT_TEXT_PRIMARY};
}}
QTableWidget#hf_results_table::item:selected {{
    background-color: {LIGHT_ACCENT_TINT_STRONG};
    color: {LIGHT_ACCENT_TEXT};
}}
QTableWidget#hf_results_table::item:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
}}
QHeaderView#hf_results_table::section {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    border-bottom: 1px solid {LIGHT_BORDER};
    border-right: none;
}}
QHeaderView#hf_results_table::section:hover {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    color: {LIGHT_TEXT_PRIMARY};
}}
QHeaderView#hf_results_table::section:pressed {{
    background-color: {LIGHT_BORDER};
}}
QHeaderView#hf_results_table::up-arrow {{
    image: none;
    width: 8px; height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {LIGHT_ACCENT};
    margin-right: 4px;
}}
QHeaderView#hf_results_table::down-arrow {{
    image: none;
    width: 8px; height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {LIGHT_ACCENT};
    margin-right: 4px;
}}

QProgressBar#hf_dl_progress {{
    background-color: {LIGHT_BORDER};
    border: none;
    border-radius: 2px;
}}
QProgressBar#hf_dl_progress::chunk {{
    background-color: {LIGHT_ACCENT};
    border-radius: 2px;
}}

QProgressBar#dl_progress {{
    background: rgba(113, 113, 122, 0.10);
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    color: {LIGHT_ACCENT_TEXT};
    font-size: 11px;
    font-weight: 600;
}}
QProgressBar#dl_progress::chunk {{
    background: rgba(99, 102, 241, 0.40);
    border-radius: 3px;
}}

/* ── Model status chips ── */

QLabel#chip_none {{
    background: rgba(113, 113, 122, 0.12);
    color: {LIGHT_TEXT_SECONDARY};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_loading {{
    background: rgba(99, 102, 241, 0.10);
    color: {LIGHT_ACCENT_TEXT};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_ready {{
    background: rgba(5, 150, 105, 0.12);
    color: {LIGHT_SUCCESS};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#chip_error {{
    background: rgba(220, 38, 38, 0.10);
    color: {LIGHT_ERROR};
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton#chip_cancel_btn {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER_HOVER};
    border-radius: 9999px;
    font-size: 11px;
    padding: 2px 10px;
    min-height: 22px;
}}
QPushButton#chip_cancel_btn:hover {{
    color: {LIGHT_ERROR};
    border-color: {LIGHT_ERROR};
    background-color: rgba(220, 38, 38, 0.06);
}}

QLabel#pipeline_dirty_label {{
    color: {LIGHT_WARNING};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}

/* ── HF Token contextual banner ── */

QFrame#token_banner {{
    background: rgba(217, 119, 6, 0.06);
    border: 1px solid rgba(217, 119, 6, 0.22);
    border-radius: 6px;
}}

/* ── Model meta-tags ── */

QLabel#speed_fast {{
    background: rgba(5, 150, 105, 0.08);
    color: {LIGHT_SUCCESS};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#speed_medium {{
    background: rgba(217, 119, 6, 0.08);
    color: {LIGHT_WARNING};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#speed_slow {{
    background: rgba(220, 38, 38, 0.08);
    color: {LIGHT_ERROR};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#lang_tag {{
    background: rgba(113, 113, 122, 0.10);
    color: {LIGHT_TEXT_SECONDARY};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#recommended_badge {{
    background: rgba(99, 102, 241, 0.10);
    color: {LIGHT_ACCENT_TEXT};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
}}

/* ── Custom model badges ── */

QLabel#custom_badge {{
    background: rgba(217, 119, 6, 0.10);
    color: {LIGHT_WARNING};
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QPushButton#custom_del_btn {{
    background-color: transparent;
    color: {LIGHT_TEXT_SECONDARY};
    border: none;
    border-radius: 9999px;
    font-size: 11px;
    padding: 0;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}
QPushButton#custom_del_btn:hover {{
    color: {LIGHT_ERROR};
    background-color: rgba(220, 38, 38, 0.10);
}}

/* ── Processing screen progress bars ── */

QProgressBar#stage_bar {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {LIGHT_TEXT_PRIMARY};
    min-height: 8px;
    max-height: 8px;
    font-size: 10px;
}}
QProgressBar#stage_bar::chunk {{
    background-color: {LIGHT_ACCENT};
    border-radius: 3px;
}}
QProgressBar#stage_bar[status="done"]::chunk {{
    background-color: {LIGHT_SUCCESS};
}}
QProgressBar#stage_bar[status="error"]::chunk {{
    background-color: {LIGHT_ERROR};
}}

QProgressBar#seg_bar {{
    background-color: {LIGHT_SURFACE_ELEVATED};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {LIGHT_TEXT_PRIMARY};
    min-height: 20px;
    max-height: 20px;
    font-size: 12px;
}}
QProgressBar#seg_bar::chunk {{
    background-color: {LIGHT_ACCENT};
    border-radius: 3px;
}}

/* ── Stage timeline pills ── */
QLabel#stage_pill {{
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    color: {LIGHT_TEXT_SECONDARY};
    background: transparent;
}}
QLabel#stage_pill[stage_state="active"] {{
    color: {LIGHT_TEXT_PRIMARY};
    font-weight: bold;
}}
QLabel#stage_pill[stage_state="done"] {{
    color: {LIGHT_SUCCESS};
}}
QLabel#stage_pill[stage_state="error"] {{
    color: {LIGHT_ERROR};
}}
QLabel#stage_sep {{
    color: {LIGHT_TEXT_SECONDARY};
    font-size: 10px;
    background: transparent;
}}

/* ── Model download label ── */
QLabel#proc_download_label {{
    font-size: 12px;
    color: {LIGHT_WARNING};
    background: transparent;
    padding: 2px 0;
}}

/* ── Tooltip ── */

QToolTip {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER_HOVER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""


_active_mode: str = "dark"


class _ThemeColors:
    __slots__ = ("bg", "bg_base", "border", "text", "accent", "error")

    def __init__(
        self, bg: str, bg_base: str, border: str, text: str, accent: str, error: str
    ) -> None:
        self.bg = bg
        self.bg_base = bg_base
        self.border = border
        self.text = text
        self.accent = accent
        self.error = error


def current_theme_colors() -> _ThemeColors:
    """Returns semantic color tokens for the active theme (dark or light).

    Call this inside paintEvent / event handlers — not at module level —
    so the result always reflects the theme that is currently applied.
    """
    if _active_mode == "light":
        return _ThemeColors(
            bg=LIGHT_SURFACE,
            bg_base=LIGHT_BG,
            border=LIGHT_BORDER,
            text=LIGHT_TEXT_SECONDARY,
            accent=LIGHT_ACCENT,
            error=LIGHT_ERROR,
        )
    return _ThemeColors(
        bg=BG_SURFACE,
        bg_base=BG_BASE,
        border=BORDER,
        text=TEXT_MUTED,
        accent=ACCENT,
        error=ERROR,
    )


def apply_theme(app: QApplication, scale: float = 1.0, mode: str = "dark") -> None:
    """Применяет тему к QApplication.

    Устанавливает QPalette с цветами приложения и глобальный QSS stylesheet.
    Все px-значения в QSS умножаются на ``scale``.

    Args:
        app: Экземпляр приложения для применения темы.
        scale: Коэффициент масштабирования (по умолчанию 1.0).
        mode: Тема — ``"dark"`` (по умолчанию) или ``"light"``.
    """
    global _active_mode
    _active_mode = mode

    from ui.qt.scale_manager import scale_qss

    palette = QPalette()
    if mode == "light":
        palette.setColor(QPalette.ColorRole.Window, QColor(LIGHT_BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(LIGHT_TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(LIGHT_SURFACE_ELEVATED))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(LIGHT_SURFACE))
        palette.setColor(QPalette.ColorRole.Text, QColor(LIGHT_TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(LIGHT_SURFACE))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(LIGHT_TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(LIGHT_ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(LIGHT_TEXT_SECONDARY))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(LIGHT_SURFACE))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(LIGHT_TEXT_PRIMARY))
        app.setPalette(palette)
        app.setStyleSheet(scale_qss(LIGHT_QSS, scale))
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor(BG_BASE))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(BG_INPUT))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(BG_SURFACE))
        palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(BG_SURFACE))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(BG_SURFACE))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT_PRIMARY))
        app.setPalette(palette)
        app.setStyleSheet(scale_qss(DARK_QSS, scale))
