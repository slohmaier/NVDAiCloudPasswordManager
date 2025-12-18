# iCloud Password Manager NVDA Add-on
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# This add-on is licensed under the GNU General Public License version 2.

import globalPluginHandler
import api
import controlTypes
import winUser


# iCloud dialog identifiers
ICLOUD_DIALOG_CLASS = "#32770"
ICLOUD_TITLE_AUTOMATION_ID = "1006"
ICLOUD_CODE_AUTOMATION_ID = "1001"


def isICloudDialog(obj):
	"""Check if the given object is an iCloud verification code dialog."""
	if obj.windowClassName != ICLOUD_DIALOG_CLASS:
		return False

	# Check children for iCloud-specific text
	try:
		for child in obj.children:
			name = child.name or ""
			if "iCloud" in name:
				return True
	except Exception:
		pass

	return False


def getVerificationCode(obj):
	"""Extract the verification code from an iCloud dialog."""
	try:
		for child in obj.children:
			# The code is typically in a Static control with AutomationId 1001
			# Format: "XXX XXX" (6 digits with space)
			name = child.name or ""
			if (child.role == controlTypes.Role.STATICTEXT and
				len(name) == 7 and
				name[3] == " " and
				name[:3].isdigit() and
				name[4:].isdigit()):
				return name
	except Exception:
		pass

	return None


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to detect iCloud verification code popups."""

	def event_foreground(self, obj, nextHandler):
		"""Handle foreground events to detect iCloud dialogs."""
		if isICloudDialog(obj):
			# iCloud dialog detected - currently doing nothing
			# Future: announce the code, copy to clipboard, etc.
			pass

		nextHandler()
