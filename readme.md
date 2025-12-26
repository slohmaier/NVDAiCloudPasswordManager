# iCloud Password Manager for NVDA

An NVDA add-on that makes iCloud Password Manager popups accessible for screen reader users.

## Features

### Verification Code Announcements
When an iCloud verification code dialog appears (e.g., during two-factor authentication), the add-on:
- Automatically detects the popup
- Announces the 6-digit code with spaces between digits for clarity (e.g., "iCloud code: 1 2 3 4 5 6")
- Provides a hint on how to repeat the code (NVDA+Tab)

### Password Save Dialog Support
For iCloud password save dialogs (without verification codes):
- Automatically focuses the dialog
- Moves focus to the first button for easy interaction
- Announces the button name

## Requirements

- NVDA 2024.1 or later
- iCloud for Windows with the iCloud Passwords browser extension

## Installation

1. Download the latest `.nvda-addon` file from the releases
2. Open the file with NVDA running to install
3. Restart NVDA when prompted

## Usage

The add-on works automatically in the background. When you:

1. **Receive a verification code**: The code will be announced automatically. Use NVDA+Tab to hear the current focus again if needed.

2. **See a password save prompt**: The dialog will be focused and the first button announced.

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
