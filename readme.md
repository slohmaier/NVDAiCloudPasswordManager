# iCloud Password Manager for NVDA

An NVDA add-on that makes iCloud Password Manager popups accessible for screen reader users.

## Features

### Verification Code Detection & Auto-Entry
When an iCloud verification code dialog appears (e.g., during two-factor authentication), the add-on:
- Automatically detects the popup
- Announces the 6-digit code with spaces between digits for clarity (e.g., "iCloud code: 1 2 3 4 5 6")
- Auto-types the code into the iCloud Passwords Edge extension PIN fields when they receive focus

### Password Save Dialog
When iCloud prompts to save a password:
- Dialog automatically steals focus from the browser
- Full dialog text is announced along with available buttons
- Tab/Shift+Tab cycles between "Save Password" and "Not Now" buttons
- Each Tab press reads the dialog message and focused button name
- Enter/Space activates the focused button

### Credential Autofill List
When the iCloud Passwords Edge extension shows a dropdown of saved credentials on a login page:
- NVDA reads the credential items instead of "blank"
- Arrow keys navigate between credentials with proper announcements

### Main Window Accessibility
In the iCloud Passwords desktop application:
- The previously unlabeled Add (+) and Sort toolbar buttons now announce proper names
- Saved credential list items read their title and username (e.g., "gitea slohmaier, slohmaier") instead of just "List Item"
- The unlabeled chevron button next to the shared-group label on a credential's detail view is now announced as "Change group"

## Requirements

- NVDA 2024.1 or later
- iCloud for Windows with the iCloud Passwords browser extension

## Installation

1. Download the latest `.nvda-addon` file from the [releases](https://github.com/slohmaier/NVDAiCloudPasswordManager/releases)
2. Open the file with NVDA running to install
3. Restart NVDA when prompted

## Usage

The add-on works automatically in the background. When you:

1. **Receive a verification code**: The code will be announced automatically and auto-typed into PIN fields.

2. **See a password save prompt**: The dialog will steal focus. Use Tab/Shift+Tab to navigate between buttons, Enter/Space to activate.

3. **See a credential autofill dropdown**: Use arrow keys to navigate. NVDA will read the credential names instead of "blank".

## Building from Source

```powershell
# Build the addon
scons

# Build development version
scons dev=1
```

## License

This add-on is licensed under the GNU General Public License version 2.

Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
