#!/bin/bash

# ==============================================================================
# UNIFIED DEFENSE - INSTALLER
# Self-contained Claude Code protection system
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.claude/hooks/unified-defense"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         UNIFIED DEFENSE - Claude Code Protection             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Check Prerequisites
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/4]${NC} Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    echo "Please install Python 3.6+ to continue."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ✓ Python ${PYTHON_VERSION} found"

# Check if Claude settings directory exists
mkdir -p "$HOME/.claude"
echo -e "  ✓ Claude directory ready"

# ------------------------------------------------------------------------------
# 2. Install Hooks
# ------------------------------------------------------------------------------
echo -e "${BLUE}[2/4]${NC} Installing hooks to ${INSTALL_DIR}..."

# Create installation directory
mkdir -p "$INSTALL_DIR/hooks"
mkdir -p "$INSTALL_DIR/config"

# Copy hooks
cp "$SCRIPT_DIR/hooks/bash_guard.py" "$INSTALL_DIR/hooks/"
cp "$SCRIPT_DIR/hooks/edit_guard.py" "$INSTALL_DIR/hooks/"
chmod +x "$INSTALL_DIR/hooks/bash_guard.py"
chmod +x "$INSTALL_DIR/hooks/edit_guard.py"

echo -e "  ✓ bash_guard.py installed"
echo -e "  ✓ edit_guard.py installed"

# ------------------------------------------------------------------------------
# 3. Install Configuration
# ------------------------------------------------------------------------------
echo -e "${BLUE}[3/4]${NC} Installing configuration..."

if [ -f "$INSTALL_DIR/config/patterns.yaml" ]; then
    echo -e "  ${YELLOW}! patterns.yaml already exists, creating backup...${NC}"
    cp "$INSTALL_DIR/config/patterns.yaml" "$INSTALL_DIR/config/patterns.yaml.bak.$(date +%s)"
fi

cp "$SCRIPT_DIR/config/patterns.yaml" "$INSTALL_DIR/config/"
echo -e "  ✓ patterns.yaml installed"

# ------------------------------------------------------------------------------
# 4. Update Claude Settings
# ------------------------------------------------------------------------------
echo -e "${BLUE}[4/4]${NC} Configuring Claude Code hooks..."

# Backup existing settings
if [ -f "$SETTINGS_FILE" ]; then
    BACKUP_FILE="$HOME/.claude/settings.json.bak.$(date +%s)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo -e "  ✓ Backed up existing settings to $(basename $BACKUP_FILE)"
else
    echo '{}' > "$SETTINGS_FILE"
fi

# Use Python to safely merge settings (no external YAML/JSON dependencies)
python3 << 'PYTHON_SCRIPT'
import json
import os
import sys

settings_path = os.path.expanduser("~/.claude/settings.json")
hooks_dir = os.path.expanduser("~/.claude/hooks/unified-defense")

# Load existing settings
try:
    with open(settings_path, "r") as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    data = {}

# Ensure hooks structure exists
if "hooks" not in data:
    data["hooks"] = {}

# Define the PreToolUse hooks
pre_tool_use = data["hooks"].get("PreToolUse", [])

# Remove any existing unified-defense hooks
pre_tool_use = [h for h in pre_tool_use if not (
    isinstance(h, dict) and 
    "hooks" in h and 
    any("unified-defense" in str(hook.get("command", "")) for hook in h.get("hooks", []) if isinstance(hook, dict))
)]

# Add our hooks
bash_hook = {
    "matcher": "Bash",
    "hooks": [
        {
            "type": "command",
            "command": f"python3 {hooks_dir}/hooks/bash_guard.py",
            "timeout": 5
        }
    ]
}

edit_hook = {
    "matcher": "Edit", 
    "hooks": [
        {
            "type": "command",
            "command": f"python3 {hooks_dir}/hooks/edit_guard.py",
            "timeout": 5
        }
    ]
}

# Also hook Write tool (Claude's file write tool)
write_hook = {
    "matcher": "Write",
    "hooks": [
        {
            "type": "command", 
            "command": f"python3 {hooks_dir}/hooks/edit_guard.py",
            "timeout": 5
        }
    ]
}

pre_tool_use.extend([bash_hook, edit_hook, write_hook])
data["hooks"]["PreToolUse"] = pre_tool_use

# Save settings
with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)

print("  ✓ Claude settings updated")
PYTHON_SCRIPT

# ------------------------------------------------------------------------------
# Done!
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Installation Complete!                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Hooks installed to:${NC}     $INSTALL_DIR"
echo -e "  ${BLUE}Configuration:${NC}          $INSTALL_DIR/config/patterns.yaml"
echo -e "  ${BLUE}Claude settings:${NC}        $SETTINGS_FILE"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Restart any running Claude Code sessions"
echo -e "  2. Edit ${INSTALL_DIR}/config/patterns.yaml to customize protection"
echo -e "  3. Add your safe zones (project directories) to patterns.yaml"
echo ""
echo -e "${BLUE}To uninstall, run:${NC} ./uninstall.sh"
