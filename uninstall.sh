#!/bin/bash

# ==============================================================================
# UNIFIED DEFENSE - UNINSTALLER
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="$HOME/.claude/hooks/unified-defense"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo -e "${BLUE}Uninstalling Unified Defense...${NC}"

# Remove hooks from settings
if [ -f "$SETTINGS_FILE" ]; then
    python3 << 'PYTHON_SCRIPT'
import json
import os

settings_path = os.path.expanduser("~/.claude/settings.json")

try:
    with open(settings_path, "r") as f:
        data = json.load(f)
except:
    exit(0)

if "hooks" in data and "PreToolUse" in data["hooks"]:
    # Remove unified-defense hooks
    data["hooks"]["PreToolUse"] = [
        h for h in data["hooks"]["PreToolUse"] 
        if not (isinstance(h, dict) and any(
            "unified-defense" in str(hook.get("command", "")) 
            for hook in h.get("hooks", []) if isinstance(hook, dict)
        ))
    ]
    
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)

print("  ✓ Removed hooks from Claude settings")
PYTHON_SCRIPT
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "  ✓ Removed $INSTALL_DIR"
fi

echo -e "${GREEN}Unified Defense has been uninstalled.${NC}"
