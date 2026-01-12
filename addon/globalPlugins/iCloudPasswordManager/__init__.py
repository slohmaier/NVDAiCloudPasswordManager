# iCloud Password Manager NVDA Add-on
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# This add-on is licensed under the GNU General Public License version 2.

import re
import api
import eventHandler
import globalPluginHandler
import inputCore
import speech
from logHandler import log

# iCloud dialog identifiers
ICLOUD_DIALOG_CLASS = "#32770"

# Regex to match verification code (6 digits, possibly with space in middle)
VERIFICATION_CODE_PATTERN = re.compile(r"\b(\d{3})\s?(\d{3})\b")


def isICloudDialog(obj):
	"""Check if an NVDA object is an iCloud dialog."""
	try:
		if obj and obj.windowClassName == ICLOUD_DIALOG_CLASS:
			for child in obj.children:
				name = child.name or ""
				if "iCloud" in name:
					return True
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error checking object: {e}")
	return False


def findVerificationCode(obj):
	"""Search for a 6-digit verification code in the dialog's children."""
	try:
		for child in obj.recursiveDescendants:
			name = child.name or ""
			match = VERIFICATION_CODE_PATTERN.search(name)
			if match:
				code = match.group(1) + match.group(2)
				log.info(f"iCloudPasswordManager: Found verification code: {code}")
				return code
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error searching for code: {e}")
	return None


def findFirstButton(obj):
	"""Find the first button in the dialog."""
	try:
		for child in obj.recursiveDescendants:
			if child.role == 9:  # ROLE_BUTTON = 9
				log.info(f"iCloudPasswordManager: Found button: '{child.name}'")
				return child
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error searching for button: {e}")
	return None


def getRepeatGestureHint():
	"""Get the gesture for repeating last speech, or a hint if not configured."""
	try:
		allGestures = inputCore.manager.getAllGestureMappings()
		for category, gestures in allGestures.items():
			for gestureInfo in gestures.values():
				scriptName = gestureInfo.scriptName if hasattr(gestureInfo, "scriptName") else ""
				if "reportCurrentFocus" in scriptName or "Focus" in str(gestureInfo):
					if hasattr(gestureInfo, "gestures") and gestureInfo.gestures:
						gesture = list(gestureInfo.gestures)[0]
						return f"Press {gesture.replace('kb:', '')} to hear focus"
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error getting gesture: {e}")
	return "Press NVDA+Tab to hear focus again"


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to detect and announce iCloud verification codes."""

	def __init__(self):
		super().__init__()
		log.info("iCloudPasswordManager: Plugin initialized (event-driven)")
		self._lastHandledHwnd = None
		self._repeatHint = getRepeatGestureHint()

	def event_foreground(self, obj, nextHandler):
		"""Called when a window comes to the foreground."""
		try:
			hwnd = obj.windowHandle
			if hwnd and hwnd != self._lastHandledHwnd and isICloudDialog(obj):
				self._lastHandledHwnd = hwnd
				log.info(f"iCloudPasswordManager: iCloud dialog foregrounded hwnd={hwnd}")
				self._handleICloudDialog(obj)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error in event_foreground: {e}")
		nextHandler()

	def _handleICloudDialog(self, obj):
		"""Handle an iCloud dialog - announce code or focus button."""
		code = findVerificationCode(obj)
		if code:
			spaced_code = " ".join(code)
			log.info(f"iCloudPasswordManager: Announcing code: {code}")
			speech.speakMessage(f"iCloud code: {spaced_code}. {self._repeatHint}")
		else:
			log.info("iCloudPasswordManager: No code, focusing dialog")
			api.setFocusObject(obj)
			eventHandler.queueEvent("gainFocus", obj)
			button = findFirstButton(obj)
			if button:
				log.info(f"iCloudPasswordManager: Focusing button: '{button.name}'")
				api.setFocusObject(button)
				eventHandler.queueEvent("gainFocus", button)
				speech.speakMessage(f"iCloud dialog: {button.name}")
