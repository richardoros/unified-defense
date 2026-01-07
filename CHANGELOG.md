# Changelog

All notable changes to Unified Defense will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-01-07

### 🎉 Initial Release

First public release of Unified Defense — a self-contained protection system for Claude Code.

### Added

#### Core Protection
- **Bash Guard** (`bash_guard.py`) — Intercepts and validates shell commands
- **Edit Guard** (`edit_guard.py`) — Intercepts and validates file write operations
- **Pattern Configuration** (`patterns.yaml`) — Flexible YAML-based security rules

#### Security Features
- 🚫 **Dangerous Command Blocking** — Blocks `rm -rf /`, `chmod 777`, fork bombs, pipe-to-shell attacks
- 🔒 **Protected Paths** — Guards `.env`, `.ssh/`, `.aws/`, private keys, system directories
- 📋 **Blocklist Mode** — Default mode, blocks only known dangerous patterns
- 🔐 **Whitelist Mode** — Paranoid mode, blocks everything except explicit safe zones

#### Observability
- 📝 **Audit Logging** — All decisions logged to `~/.claude/defense.log`
- 📊 **Statistics Tracking** — Block/allow counts tracked in logs

#### User Interface
- 🖥️ **Terminal Dashboard** (`defense.py`) — Interactive curses-based management UI
- ⚙️ **Live Configuration** — Toggle mode and logging without editing files
- 📜 **Log Viewer** — View recent activity from the dashboard

#### Installation
- 📦 **One-Click Install** (`install.sh`) — Copies hooks to `~/.claude/hooks/`
- 🗑️ **Clean Uninstall** (`uninstall.sh`) — Removes all traces
- ⚡ **Zero Dependencies** — Pure Python 3.6+, no pip packages required

### Technical Details

- **Hook Protocol**: Exit code 0 = Allow, Exit code 2 = Block (with reason on stderr)
- **Config Location**: `~/.claude/hooks/unified-defense/config/patterns.yaml`
- **Log Location**: `~/.claude/defense.log`
- **Compatible with**: Claude Code CLI

---

## [Unreleased]

### Planned
- [ ] Project-specific overrides (`.claude/defense.yaml` in project root)
- [ ] Time-based rules (allow certain operations only during work hours)
- [ ] Integration with Claude Code's permission system
- [ ] Web-based dashboard option
- [ ] Command history analysis and recommendations
