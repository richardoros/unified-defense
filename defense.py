#!/usr/bin/env python3
"""
Unified Defense - Terminal Management UI
Interactive dashboard for managing the defense system.
"""

import curses
import os
import sys
from datetime import datetime
from pathlib import Path


def get_config_path() -> Path:
    """Get the path to patterns.yaml configuration file."""
    # Check for config in the same directory as the script
    script_dir = Path(__file__).parent
    config_path = script_dir / "config" / "patterns.yaml"
    
    if config_path.exists():
        return config_path
    
    # Fallback to ~/.claude/hooks/unified-defense/config/
    fallback = Path.home() / ".claude" / "hooks" / "unified-defense" / "config" / "patterns.yaml"
    if fallback.exists():
        return fallback
    
    return config_path  # Return default even if not exists


def load_settings() -> dict:
    """Load settings from patterns.yaml."""
    config_path = get_config_path()
    settings = {
        "mode": "blocklist",
        "logging": False,
        "log_file": "~/.claude/defense.log"
    }
    
    if not config_path.exists():
        return settings
    
    with open(config_path, "r") as f:
        in_settings = False
        for line in f:
            line = line.rstrip()
            if line.startswith("settings:"):
                in_settings = True
                continue
            if in_settings and line and not line.startswith(" ") and not line.startswith("#"):
                break
            if in_settings:
                stripped = line.strip()
                if stripped.startswith("mode:"):
                    settings["mode"] = stripped.split(":", 1)[1].strip().strip('"')
                elif stripped.startswith("logging:"):
                    val = stripped.split(":", 1)[1].strip().lower()
                    settings["logging"] = val in ("true", "yes", "1")
                elif stripped.startswith("log_file:"):
                    settings["log_file"] = stripped.split(":", 1)[1].strip().strip('"')
    
    return settings


def save_setting(key: str, value: str):
    """Update a setting in patterns.yaml."""
    config_path = get_config_path()
    if not config_path.exists():
        return
    
    with open(config_path, "r") as f:
        lines = f.readlines()
    
    in_settings = False
    for i, line in enumerate(lines):
        if line.strip().startswith("settings:"):
            in_settings = True
            continue
        if in_settings and line.strip() and not line.startswith(" ") and not line.startswith("#"):
            break
        if in_settings and line.strip().startswith(f"{key}:"):
            # Replace the value
            indent = len(line) - len(line.lstrip())
            lines[i] = " " * indent + f'{key}: "{value}"\n'
            break
    
    with open(config_path, "w") as f:
        f.writelines(lines)


def get_recent_logs(n: int = 10) -> list:
    """Get the last n log entries."""
    log_path = Path.home() / ".claude" / "defense.log"
    if not log_path.exists():
        return []
    
    with open(log_path, "r") as f:
        lines = f.readlines()
    
    return lines[-n:] if len(lines) > n else lines


def count_stats() -> dict:
    """Count block/allow stats from logs."""
    log_path = Path.home() / ".claude" / "defense.log"
    stats = {"blocks": 0, "allows": 0, "total": 0}
    
    if not log_path.exists():
        return stats
    
    with open(log_path, "r") as f:
        for line in f:
            stats["total"] += 1
            if " BLOCK:" in line:
                stats["blocks"] += 1
            elif " ALLOW:" in line:
                stats["allows"] += 1
    
    return stats


def draw_box(stdscr, y, x, h, w, title=""):
    """Draw a box with optional title."""
    # Draw corners
    stdscr.addch(y, x, curses.ACS_ULCORNER)
    stdscr.addch(y, x + w - 1, curses.ACS_URCORNER)
    stdscr.addch(y + h - 1, x, curses.ACS_LLCORNER)
    stdscr.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
    
    # Draw horizontal lines
    for i in range(1, w - 1):
        stdscr.addch(y, x + i, curses.ACS_HLINE)
        stdscr.addch(y + h - 1, x + i, curses.ACS_HLINE)
    
    # Draw vertical lines
    for i in range(1, h - 1):
        stdscr.addch(y + i, x, curses.ACS_VLINE)
        stdscr.addch(y + i, x + w - 1, curses.ACS_VLINE)
    
    # Draw title
    if title:
        stdscr.addstr(y, x + 2, f" {title} ")


def main(stdscr):
    """Main UI loop."""
    # Setup colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Allow
    curses.init_pair(2, curses.COLOR_RED, -1)     # Block
    curses.init_pair(3, curses.COLOR_CYAN, -1)    # Header
    curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Warning
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected
    
    curses.curs_set(0)  # Hide cursor
    stdscr.timeout(1000)  # Refresh every second
    
    selected = 0
    menu_items = ["Toggle Mode", "Toggle Logging", "View Logs", "Refresh", "Quit"]
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Load current settings
        settings = load_settings()
        stats = count_stats()
        
        # Header
        title = "╔══════════════════════════════════════════╗"
        subtitle = "║     🛡️  UNIFIED DEFENSE DASHBOARD  🛡️     ║"
        footer = "╚══════════════════════════════════════════╝"
        
        try:
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.color_pair(3))
            stdscr.addstr(2, (width - len(subtitle)) // 2, subtitle, curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(3, (width - len(footer)) // 2, footer, curses.color_pair(3))
        except curses.error:
            pass
        
        # Status panel
        panel_y = 5
        panel_x = 2
        panel_w = min(44, width - 4)
        
        try:
            stdscr.addstr(panel_y, panel_x, "STATUS", curses.A_BOLD | curses.color_pair(3))
            stdscr.addstr(panel_y, panel_x + 7, "─" * (panel_w - 7))
            
            # Mode
            mode_color = curses.color_pair(4) if settings["mode"] == "whitelist" else curses.color_pair(1)
            mode_label = "🔒 WHITELIST (Paranoid)" if settings["mode"] == "whitelist" else "📋 BLOCKLIST (Normal)"
            stdscr.addstr(panel_y + 1, panel_x, f"Mode:    {mode_label}", mode_color)
            
            # Logging
            log_status = "✅ ENABLED" if settings["logging"] else "❌ DISABLED"
            log_color = curses.color_pair(1) if settings["logging"] else curses.color_pair(2)
            stdscr.addstr(panel_y + 2, panel_x, f"Logging: {log_status}", log_color)
            
            # Stats
            stdscr.addstr(panel_y + 4, panel_x, "STATISTICS", curses.A_BOLD | curses.color_pair(3))
            stdscr.addstr(panel_y + 4, panel_x + 11, "─" * (panel_w - 11))
            stdscr.addstr(panel_y + 5, panel_x, f"Total:   {stats['total']} decisions")
            stdscr.addstr(panel_y + 6, panel_x, f"Blocked: {stats['blocks']}", curses.color_pair(2))
            stdscr.addstr(panel_y + 7, panel_x, f"Allowed: {stats['allows']}", curses.color_pair(1))
        except curses.error:
            pass
        
        # Menu
        menu_y = panel_y + 9
        try:
            stdscr.addstr(menu_y, panel_x, "ACTIONS", curses.A_BOLD | curses.color_pair(3))
            stdscr.addstr(menu_y, panel_x + 8, "─" * (panel_w - 8))
            
            for i, item in enumerate(menu_items):
                y = menu_y + 1 + i
                if i == selected:
                    stdscr.addstr(y, panel_x, f" ▶ {item} ", curses.color_pair(5) | curses.A_BOLD)
                else:
                    stdscr.addstr(y, panel_x, f"   {item}")
        except curses.error:
            pass
        
        # Recent logs panel
        logs_y = panel_y
        logs_x = panel_w + 6
        logs_w = width - logs_x - 2
        
        if logs_w > 20:
            try:
                stdscr.addstr(logs_y, logs_x, "RECENT ACTIVITY", curses.A_BOLD | curses.color_pair(3))
                stdscr.addstr(logs_y, logs_x + 16, "─" * (logs_w - 16))
                
                logs = get_recent_logs(12)
                for i, log in enumerate(logs):
                    if logs_y + 1 + i >= height - 2:
                        break
                    # Parse and format log entry
                    log = log.strip()
                    if " BLOCK:" in log:
                        color = curses.color_pair(2)
                        symbol = "❌"
                    else:
                        color = curses.color_pair(1)
                        symbol = "✅"
                    
                    # Truncate if too long
                    display = f"{symbol} {log[:logs_w - 4]}" if len(log) > logs_w - 4 else f"{symbol} {log}"
                    stdscr.addstr(logs_y + 1 + i, logs_x, display[:logs_w], color)
            except curses.error:
                pass
        
        # Footer
        try:
            footer_text = "↑/↓: Navigate  |  Enter: Select  |  q: Quit"
            stdscr.addstr(height - 1, (width - len(footer_text)) // 2, footer_text, curses.A_DIM)
        except curses.error:
            pass
        
        stdscr.refresh()
        
        # Handle input
        key = stdscr.getch()
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(menu_items)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(menu_items)
        elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
            if selected == 0:  # Toggle Mode
                new_mode = "whitelist" if settings["mode"] == "blocklist" else "blocklist"
                save_setting("mode", new_mode)
            elif selected == 1:  # Toggle Logging
                new_logging = "false" if settings["logging"] else "true"
                save_setting("logging", new_logging)
            elif selected == 2:  # View Logs
                # Show full log view
                stdscr.clear()
                stdscr.addstr(0, 0, "FULL LOG (Press any key to return)", curses.A_BOLD)
                logs = get_recent_logs(height - 3)
                for i, log in enumerate(logs):
                    if i + 2 >= height - 1:
                        break
                    stdscr.addstr(i + 2, 0, log.strip()[:width - 1])
                stdscr.refresh()
                stdscr.timeout(-1)
                stdscr.getch()
                stdscr.timeout(1000)
            elif selected == 3:  # Refresh
                pass  # Will refresh on next loop
            elif selected == 4:  # Quit
                break


def run():
    """Entry point."""
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
