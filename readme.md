# iCloud Password Manager

An NVDA add-on that detects iCloud verification code popups and assists with password autofill workflows.

## Features

- Automatically detects when an iCloud verification code dialog appears
- Identifies the verification code from the popup (format: XXX XXX)

## How It Works

When the iCloud Passwords browser extension requests a verification code, Windows displays a popup dialog containing the 6-digit code. This add-on monitors for these dialogs by:

1. Listening for foreground window changes
2. Checking if the new window is a standard Windows dialog (`#32770` class)
3. Scanning child elements for iCloud-specific text

## Technical Details

The iCloud verification dialog has the following structure:
- Window class: `#32770` (standard Windows dialog)
- Contains text with "iCloud" in the title
- Verification code displayed as static text (format: "XXX XXX")

## Requirements

- NVDA 2023.1 or later
- Windows 10/11 with iCloud for Windows installed

## License

This add-on is licensed under the GNU General Public License version 2.

Copyright (C) 2024 Stefan Lohmaier
