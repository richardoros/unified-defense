#!/usr/bin/env python3
"""
Unified Defense - Bash Guard
Intercepts Bash commands and blocks dangerous operations.

Claude Code Hook Protocol:
- Receives JSON on stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
- Returns JSON on stdout: {"decision": "allow"|"block", "reason": "..."}
"""

import json
import os
import re
import sys
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
        "protected_paths": [],
        "dangerous_commands": [],
        "safe_zones": []
    }
    
    current_section = None
    current_item = {}
    
    with open(config_path, "r") as f:
        for line in f:
            line = line.rstrip()
            
            # Skip empty lines and comments
            if not line or line.strip().startswith("#"):
                continue
            
            # Detect top-level sections
            if line.startswith("protected_paths:"):
                current_section = "protected_paths"
                continue
            elif line.startswith("dangerous_commands:"):
                current_section = "dangerous_commands"
                continue
            elif line.startswith("safe_zones:"):
                current_section = "safe_zones"
                continue
            
            if current_section is None:
                continue
            
            # Parse list items
            stripped = line.strip()
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


def extract_paths_from_command(command: str) -> list:
    """Extract file paths from a Bash command."""
    paths = []
    
    # Common path patterns
    # Look for absolute paths
    abs_paths = re.findall(r'(?:^|\s)(/[^\s;|&<>]+)', command)
    paths.extend(abs_paths)
    
    # Look for home-relative paths
    home_paths = re.findall(r'(?:^|\s)(~[^\s;|&<>]*)', command)
    paths.extend([expand_path(p) for p in home_paths])
    
    # Look for relative paths with ./
    rel_paths = re.findall(r'(?:^|\s)(\./[^\s;|&<>]+)', command)
    paths.extend([os.path.abspath(p) for p in rel_paths])
    
    return list(set(paths))


def check_dangerous_command(command: str, patterns: list) -> Optional[str]:
    """Check if command matches any dangerous command pattern (simple substring match)."""
    command_lower = command.lower()
    for item in patterns:
        pattern = item.get("pattern", "").lower()
        if pattern and pattern in command_lower:
            return item.get("reason", "Matches dangerous command pattern")
    return None


def check_path_protection(path: str, config: dict) -> Tuple[bool, Optional[str]]:
    """
    Check if a path is protected.
    Returns (is_allowed, reason_if_blocked)
    """
    # First check safe zones (they override protection)
    for zone in config.get("safe_zones", []):
        pattern = zone.get("pattern", "")
        regex = glob_to_regex(pattern)
        if re.match(regex, path):
            return True, None
    
    # Check protected paths
    for protected in config.get("protected_paths", []):
        pattern = protected.get("pattern", "")
        level = protected.get("level", "block")
        regex = glob_to_regex(pattern)
        
        if re.match(regex, path):
            reason = protected.get("reason", f"Path matches protected pattern: {pattern}")
            if level == "block":
                return False, f"BLOCKED: {reason}"
            elif level == "read_only":
                # For Bash commands, we can't easily distinguish read vs write
                # So we'll just warn but allow (the Edit hook handles writes)
                return True, None
    
    return True, None


def process_bash_command(tool_input: dict, config: dict) -> dict:
    """Process a Bash command and determine if it should be allowed."""
    command = tool_input.get("command", "")
    
    if not command:
        return {"decision": "allow", "reason": "Empty command"}
    
    # Check for dangerous command patterns
    danger_reason = check_dangerous_command(command, config.get("dangerous_commands", []))
    if danger_reason:
        return {"decision": "block", "reason": f"Dangerous command: {danger_reason}"}
    
    # Extract and check paths
    paths = extract_paths_from_command(command)
    for path in paths:
        allowed, reason = check_path_protection(path, config)
        if not allowed:
            return {"decision": "block", "reason": reason}
    
    return {"decision": "allow", "reason": "Command passed security checks"}


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Load configuration
        config = load_config()
        
        # Process the command
        tool_input = input_data.get("tool_input", {})
        result = process_bash_command(tool_input, config)
        
        # Output result
        print(json.dumps(result))
        
    except FileNotFoundError as e:
        # Config not found - fail open with warning
        print(json.dumps({
            "decision": "allow",
            "reason": f"Warning: {str(e)}. Allowing by default."
        }))
    except json.JSONDecodeError:
        print(json.dumps({
            "decision": "allow", 
            "reason": "Invalid JSON input, allowing by default"
        }))
    except Exception as e:
        print(json.dumps({
            "decision": "allow",
            "reason": f"Hook error: {str(e)}. Allowing by default."
        }))


if __name__ == "__main__":
    main()
