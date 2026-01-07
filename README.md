# Unified Defense

A self-contained Claude Code protection system that guards against accidental damage.

## Features

- **🛡️ Bash Guard** — Blocks dangerous shell commands (`rm -rf /`, fork bombs, etc.)
- **📁 Edit Guard** — Prevents writes to sensitive files (`.env`, `.ssh/`, credentials)
- **⚙️ Configurable** — Customize protection rules via `patterns.yaml`
- **🚫 No Dependencies** — Pure Python, no external packages required

## Quick Install

```bash
chmod +x install.sh
./install.sh
```

## How It Works

Unified Defense uses [Claude Code hooks](https://docs.anthropic.com/claude-code/hooks) to intercept tool calls before they execute:

```
Claude Code → PreToolUse Hook → bash_guard.py / edit_guard.py → Allow/Block
```

### Protection Layers

1. **Dangerous Command Detection**
   - Regex patterns catch destructive commands like `rm -rf /`, `mkfs.*`, `chmod 777`
   - Blocks `curl | bash` and similar remote code execution patterns

2. **Path Protection**
   - Blocks access to secrets: `.env`, `.ssh/`, `.aws/`, `*.pem`, `*.key`
   - Read-only protection for system directories: `/etc/`, `/usr/`, `/bin/`
   - Safe zones for temporary and project directories

## Configuration

Edit `~/.claude/hooks/unified-defense/config/patterns.yaml` to customize:

```yaml
# Block access to a path
protected_paths:
  - pattern: "~/.secrets/**"
    level: block
    reason: "Custom secrets directory"

# Make a path read-only
  - pattern: "/my/important/data/**"
    level: read_only
    reason: "Important data, no modifications"

# Allow full access to a path
safe_zones:
  - pattern: "~/projects/**"
    reason: "My project directories"
```

### Protection Levels

| Level | Read | Write | Use Case |
|-------|------|-------|----------|
| `block` | ❌ | ❌ | Secrets, credentials |
| `read_only` | ✅ | ❌ | System files, configs |
| `allow` | ✅ | ✅ | Safe zones, projects |

## Uninstall

```bash
./uninstall.sh
```

## File Structure

```
unified-defense/
├── install.sh          # One-click installer
├── uninstall.sh        # Uninstaller
├── config/
│   └── patterns.yaml   # Security rules
└── hooks/
    ├── bash_guard.py   # Bash command protection
    └── edit_guard.py   # File edit protection
```

## Testing

After installation, restart Claude Code and test:

```
You: "Delete everything in my home directory"
Claude: [BLOCKED by bash_guard: Dangerous command - Recursive force delete from home]

You: "Edit my SSH config"  
Claude: [BLOCKED by edit_guard: SSH keys and configuration]
```

## License

MIT
