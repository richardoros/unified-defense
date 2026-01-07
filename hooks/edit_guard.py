#!/usr/bin/env python3
"""
Unified Defense - Edit Guard
Intercepts file edit operations and blocks writes to protected paths.

Claude Code Hook Protocol:
- Receives JSON on stdin: {"tool_name": "Edit", "tool_input": {"file_path": "..."}}
- Exit 0 = Allow, Exit 2 = Block (reason on stderr)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def get_config_path() -> Path:
    """Get the path to patterns.yaml configuration file."""
    # Check for config in the same directory as the hook
    hook_dir = Path(__file__).parent.parent
    config_path = hook_dir / "config" / "patterns.yaml"
    
    if config_path.exists():
        return config_path
    
    # Fallback to ~/.claude/hooks/unified-defense/config/
    fallback = Path.home() / ".claude" / "hooks" / "unified-defense" / "config" / "patterns.yaml"
    if fallback.exists():
        return fallback
    
    raise FileNotFoundError(f"Configuration not found at {config_path} or {fallback}")


def load_config() -> dict:
    """Load and parse the YAML configuration file."""
    config_path = get_config_path()
    
    # Simple YAML parser for our specific format (no external dependencies)
    config = {
        "settings": {
            "mode": "blocklist",
            "logging": False,
            "log_file": "~/.claude/defense.log"
        },
        "protected_paths": [],
        "dangerous_commands": [],
        "safe_zones": []
    }
    
    current_section = None
    current_item = {}
    in_settings = False
    
    with open(config_path, "r") as f:
        for line in f:
            line = line.rstrip()
            
            # Skip empty lines and comments
            if not line or line.strip().startswith("#"):
                continue
            
            # Detect top-level sections
            if line.startswith("settings:"):
                in_settings = True
                current_section = None
                continue
            elif line.startswith("protected_paths:"):
                in_settings = False
                current_section = "protected_paths"
                continue
            elif line.startswith("dangerous_commands:"):
                in_settings = False
                current_section = "dangerous_commands"
                continue
            elif line.startswith("safe_zones:"):
                in_settings = False
                current_section = "safe_zones"
                continue
            
            stripped = line.strip()
            
            # Parse settings
            if in_settings:
                if stripped.startswith("mode:"):
                    config["settings"]["mode"] = stripped.split(":", 1)[1].strip().strip('"')
                elif stripped.startswith("logging:"):
                    val = stripped.split(":", 1)[1].strip().lower()
                    config["settings"]["logging"] = val in ("true", "yes", "1")
                elif stripped.startswith("log_file:"):
                    config["settings"]["log_file"] = stripped.split(":", 1)[1].strip().strip('"')
                continue
            
            if current_section is None:
                continue
            
            # Parse list items
            if stripped.startswith("- pattern:"):
                # Save previous item if exists
                if current_item and "pattern" in current_item:
                    config[current_section].append(current_item)
                current_item = {"pattern": stripped.split(":", 1)[1].strip().strip('"')}
            elif stripped.startswith("level:"):
                current_item["level"] = stripped.split(":", 1)[1].strip().strip('"')
            elif stripped.startswith("reason:"):
                current_item["reason"] = stripped.split(":", 1)[1].strip().strip('"')
    
    # Don't forget the last item
    if current_item and "pattern" in current_item:
        config[current_section].append(current_item)
    
    return config


def log_decision(config: dict, decision: str, file_path: str, reason: str):
    """Log a decision to the audit log file."""
    settings = config.get("settings", {})
    if not settings.get("logging", False):
        return
    
    log_file = os.path.expanduser(settings.get("log_file", "~/.claude/defense.log"))
    log_dir = os.path.dirname(log_file)
    
    try:
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] EDIT {decision.upper()}: {file_path} | {reason}\n"
        
        with open(log_file, "a") as f:
            f.write(log_entry)
    except Exception:
        # Don't let logging failures break the hook
        pass


def expand_path(pattern: str) -> str:
    """Expand ~ and environment variables in path patterns."""
    pattern = os.path.expanduser(pattern)
    pattern = os.path.expandvars(pattern)
    return pattern


def glob_to_regex(pattern: str) -> str:
    """Convert a glob pattern to a regex pattern."""
    pattern = expand_path(pattern)
    
    # Escape special regex characters (except * and ?)
    result = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                # ** matches any path including /
                result += ".*"
                i += 2
                # Skip trailing /
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
                continue
            else:
                # * matches anything except /
                result += "[^/]*"
        elif c == "?":
            result += "[^/]"
        elif c in ".^$+{}[]|()":
            result += "\\" + c
        else:
            result += c
        i += 1
    
    return f"^{result}$"


def normalize_path(file_path: str) -> str:
    """Normalize a file path to absolute form."""
    file_path = os.path.expanduser(file_path)
    file_path = os.path.expandvars(file_path)
    file_path = os.path.abspath(file_path)
    return file_path


def is_path_in_safe_zone(path: str, config: dict) -> bool:
    """Check if a path is in a safe zone."""
    normalized = normalize_path(path)
    for zone in config.get("safe_zones", []):
        pattern = zone.get("pattern", "")
        regex = glob_to_regex(pattern)
        if re.match(regex, normalized):
            return True
    return False


def check_path_protection(path: str, config: dict, is_write: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Check if a path is protected for the given operation.
    Returns (is_allowed, reason_if_blocked)
    """
    normalized = normalize_path(path)
    mode = config.get("settings", {}).get("mode", "blocklist")
    
    # First check safe zones (they always allow)
    if is_path_in_safe_zone(path, config):
        return True, None
    
    # In whitelist mode, if not in safe zone, block
    if mode == "whitelist":
        return False, "BLOCKED: Path not in safe zones (whitelist mode)"
    
    # Blocklist mode: check protected paths
    for protected in config.get("protected_paths", []):
        pattern = protected.get("pattern", "")
        level = protected.get("level", "block")
        regex = glob_to_regex(pattern)
        
        if re.match(regex, normalized):
            reason = protected.get("reason", f"Path matches protected pattern: {pattern}")
            
            if level == "block":
                return False, f"BLOCKED: {reason}"
            elif level == "read_only" and is_write:
                return False, f"READ-ONLY: {reason}"
    
    return True, None


def process_edit_operation(tool_input: dict, config: dict) -> dict:
    """Process a file edit operation and determine if it should be allowed."""
    # Claude Code may use different field names for the file path
    file_path = (
        tool_input.get("file_path") or 
        tool_input.get("path") or 
        tool_input.get("target") or
        tool_input.get("file")
    )
    
    if not file_path:
        return {"decision": "allow", "reason": "No file path specified"}
    
    # Check if path is protected (edits are always writes)
    allowed, reason = check_path_protection(file_path, config, is_write=True)
    
    if not allowed:
        return {"decision": "block", "reason": reason}
    
    return {"decision": "allow", "reason": "File edit passed security checks"}


def main():
    """Main entry point for the hook."""
    config = None
    file_path = ""
    
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Load configuration
        config = load_config()
        
        # Process the edit operation
        tool_input = input_data.get("tool_input", {})
        file_path = (
            tool_input.get("file_path") or 
            tool_input.get("path") or 
            tool_input.get("target") or
            tool_input.get("file") or
            ""
        )
        result = process_edit_operation(tool_input, config)
        
        # Log the decision
        log_decision(config, result["decision"], file_path, result["reason"])
        
        # Handle decision per Claude Code hook protocol:
        # - Exit 0 = Allow
        # - Exit 2 = Block (with reason on stderr)
        if result["decision"] == "block":
            print(f"[Unified Defense] {result['reason']}", file=sys.stderr)
            sys.exit(2)
        else:
            # Allow - exit 0
            sys.exit(0)
        
    except FileNotFoundError as e:
        # Config not found - fail open with warning
        print(f"[Unified Defense] Warning: {str(e)}. Allowing by default.", file=sys.stderr)
        sys.exit(0)
    except json.JSONDecodeError:
        print("[Unified Defense] Warning: Invalid JSON input, allowing by default.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"[Unified Defense] Hook error: {str(e)}. Allowing by default.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
