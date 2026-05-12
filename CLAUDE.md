# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NVDA add-on that makes iCloud Password Manager popups accessible for screen reader users.

### Current Features (v1.4)

1. **Verification Code Detection & Auto-Entry**: Automatically detects iCloud verification code dialogs (`#32770` popups) and announces the 6-digit code. When the Edge extension focuses its PIN entry fields, the code is auto-typed.

2. **Password Save Dialog Support**: For dialogs without verification codes, focuses the first button for easy interaction. Tab/Shift+Tab cycle between buttons with the dialog text re-announced.

3. **Credential Autofill List**: When the iCloud Passwords Edge extension shows a dropdown of saved credentials on a login page, NVDA reads the credential items instead of "blank". Uses a speech filter (`filter_speechSequence`) that intercepts "blank" and replaces it with the active credential's text via UIA.

4. **Main Window Accessibility (AppModule)**: For the iCloud Passwords desktop app (`iCloudPasswords.exe`, WinUI3), labels the unlabeled toolbar buttons (Add `m_AddButton`, Sort `m_SortButton`) and the chevron button next to `m_InternetCredentialSharedGroup` ("Change group"). Combines child TextBlocks of saved credential `ListViewItem`s in `InternetCredentialsListView` so NVDA reads "title, username" instead of bare "List Item". Implemented as `addon/appModules/icloudpasswords.py` (lowercase filename is required — NVDA lowercases the executable name before importing the appModule).

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

**Credential Autofill List** (iCloud Passwords dropdown on login pages):
- Document "Password AutoFill Completion List" with List `credentialList` inside
- Items: ClassName `selectable credential`, active item gets `selectable credential active`
- Chrome's UIA blocks child traversal on `credentialList` (E_POINTER / NULL COM pointer)
- Solution: Search all ListItem elements from the window element directly, check className for "active"
- Speech filter intercepts "blank" in `Chrome_RenderWidgetHostHWND` and replaces with credential text

**Build System**: SCons-based with custom tools in `site_scons/`. Configuration lives in `buildVars.py` - edit addon metadata there rather than in manifest templates.

## Code Style

- Uses tabs for indentation (configured in pyproject.toml)
- Line length: 110 characters
- Strict type checking enabled via pyright
- Linting via ruff (configured in pyproject.toml)

## Git Configuration

For this repo, use: `stefan@slohmaier.de` for commits.
