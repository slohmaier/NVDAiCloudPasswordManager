# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NVDA add-on that makes iCloud Password Manager popups accessible for screen reader users.

### Current Features (v1.1)

1. **Verification Code Detection & Auto-Entry**: Automatically detects iCloud verification code dialogs (`#32770` popups) and announces the 6-digit code. When the Edge extension focuses its PIN entry fields, the code is auto-typed.

2. **Password Save Dialog Support**: For dialogs without verification codes, focuses the first button for easy interaction.

## Build Commands

```powershell
# Build the addon (outputs .nvda-addon file)
scons

# Build and install to NVDA addons directory
scons install

# Build development version with timestamp
scons dev=1

# Generate translation template
scons pot
```

## Debugging Workflow

1. Build and install: `scons install`
2. Restart NVDA (or start with logging: `nvda --log-file=nvda.log`)
3. Check log for plugin errors

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

**Global Plugin Pattern**: The add-on uses NVDA's globalPluginHandler. The plugin at `addon/globalPlugins/iCloudPasswordManager/__init__.py` uses `SetWinEventHook` (via ctypes) to detect iCloud dialogs. NVDA's built-in events (`event_foreground`, `event_show`, etc.) do NOT fire for iCloud's `#32770` popups, so direct Windows event hooks are required.

**iCloud Dialog Detection** (`#32770` popup from iCloud for Windows):
- Window class: `#32770` (standard Windows dialog), name is empty
- Contains child element with "iCloud" in name (AutomationId `1006`)
- Verification code in child with AutomationId `1001`, format: `XXX XXX`
- Detected via `EVENT_OBJECT_SHOW` / `EVENT_SYSTEM_FOREGROUND` WinEvents

**Edge Extension PIN Entry** (iCloud Passwords browser extension):
- Lives inside Edge's `Chrome_WidgetWin_1` window, in an `ExtensionPopup` pane
- Document named "iCloud Passwords" with `RootWebArea` AutomationId
- 6 Edit fields: ClassName `PIN`, AutomationId `PIN0`-`PIN5` (no native HWND)
- Auto-typing triggered by `event_gainFocus` when focus lands on a PIN field

**Build System**: SCons-based with custom tools in `site_scons/`. Configuration lives in `buildVars.py` - edit addon metadata there rather than in manifest templates.

## Code Style

- Uses tabs for indentation (configured in pyproject.toml)
- Line length: 110 characters
- Strict type checking enabled via pyright
- Linting via ruff (configured in pyproject.toml)

## Git Configuration

For this repo, use: `stefan@slohmaier.de` for commits.
