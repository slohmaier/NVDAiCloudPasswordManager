# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NVDA add-on that makes iCloud Password Manager popups accessible. When an iCloud verification code dialog appears, the add-on detects it and can read the 6-digit code. For password save dialogs, it focuses the first button.

## Build Commands

```powershell
# Build the addon (outputs .nvda-addon file)
scons

# Build development version with timestamp
scons dev=1

# Generate translation template
scons pot
```

## Debugging Workflow

1. Build the addon: `scons`
2. Extract/copy the built `iCloudPasswordManager-*.nvda-addon` to the NVDA user addons directory (`%APPDATA%\nvda\addons\`)
3. Start NVDA with logging: `nvda --log-file=nvda.log`
4. Wait ~10 seconds for startup, then check log for plugin errors

## UIA Structure Analysis

Use the sibling `dumpUIA` tool to analyze Windows UI Automation structure of iCloud dialogs:

```powershell
# List all windows
python ..\dumpUIA\dumpUIA.py

# Dump specific window by title substring
python ..\dumpUIA\dumpUIA.py -w "iCloud"

# JSON output for programmatic analysis
python ..\dumpUIA\dumpUIA.py -w "iCloud" -j
```

## Architecture

**Global Plugin Pattern**: The add-on uses NVDA's globalPluginHandler. The single plugin file at `addon/globalPlugins/iCloudPasswordManager.py` registers for `event_foreground` events to detect iCloud dialogs.

**iCloud Dialog Detection**:
- Window class: `#32770` (standard Windows dialog)
- Contains child element with "iCloud" in name
- Verification code format: `XXX XXX` (6 digits with space)
- Key automation IDs: `1006` (title), `1001` (code)

**Build System**: SCons-based with custom tools in `site_scons/`. Configuration lives in `buildVars.py` - edit addon metadata there rather than in manifest templates.

## Code Style

- Uses tabs for indentation (configured in pyproject.toml)
- Line length: 110 characters
- Strict type checking enabled via pyright
- Linting via ruff (configured in pyproject.toml)

## Git Configuration

For this repo, use: `stefan@slohmaier.de` for commits.
