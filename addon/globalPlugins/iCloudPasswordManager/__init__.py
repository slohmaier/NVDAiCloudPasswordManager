# iCloud Password Manager NVDA Add-on
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# This add-on is licensed under the GNU General Public License version 2.

import ctypes
import re
import api
import eventHandler
import globalPluginHandler
import inputCore
import speech
import winUser
import wx
from logHandler import log
from NVDAObjects.IAccessible import getNVDAObjectFromEvent

user32 = ctypes.windll.user32

# iCloud dialog identifiers
ICLOUD_DIALOG_CLASS = "#32770"
CHECK_INTERVAL = 500  # milliseconds

# Regex to match verification code (6 digits, possibly with space in middle)
VERIFICATION_CODE_PATTERN = re.compile(r"\b(\d{3})\s?(\d{3})\b")


def findWindowEx(hwndParent, hwndChildAfter, lpszClass, lpszWindow):
	"""Wrapper for FindWindowExW."""
	return user32.FindWindowExW(hwndParent, hwndChildAfter, lpszClass, lpszWindow)


def getICloudDialogObject(hwnd):
	"""Get the NVDA object for an iCloud dialog, or None if not an iCloud dialog."""
	try:
		obj = getNVDAObjectFromEvent(hwnd, winUser.OBJID_CLIENT, 0)
		if obj and obj.windowClassName == ICLOUD_DIALOG_CLASS:
			for child in obj.children:
				name = child.name or ""
				if "iCloud" in name:
					log.info(f"iCloudPasswordManager: Detected iCloud dialog! hwnd={hwnd}, text='{name}'")
					return obj
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error checking hwnd={hwnd}: {e}")
	return None


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
		# Try to find gesture for speech history or similar
		# The "reportCurrentFocus" script can be used to re-hear focus
		allGestures = inputCore.manager.getAllGestureMappings()
		for category, gestures in allGestures.items():
			for gestureInfo in gestures.values():
				scriptName = gestureInfo.scriptName if hasattr(gestureInfo, "scriptName") else ""
				# Look for speech review or focus report commands
				if "reportCurrentFocus" in scriptName or "Focus" in str(gestureInfo):
					if hasattr(gestureInfo, "gestures") and gestureInfo.gestures:
						gesture = list(gestureInfo.gestures)[0]
						# Convert gesture identifier to readable form
						return f"Press {gesture.replace('kb:', '')} to hear focus"
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error getting gesture: {e}")
	# Default hint
	return "Press NVDA+Tab to hear focus again"


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to detect and announce iCloud verification codes."""

	def __init__(self):
		super().__init__()
		log.info("iCloudPasswordManager: Plugin initialized")
		self._lastHandledHwnd = None
		self._timer = wx.PyTimer(self._checkForICloudDialog)
		self._timer.Start(CHECK_INTERVAL)
		self._repeatHint = getRepeatGestureHint()

	def terminate(self):
		if self._timer:
			self._timer.Stop()
			self._timer = None

	def _checkForICloudDialog(self):
		"""Periodically check for iCloud dialogs and announce codes."""
		try:
			hwnd = findWindowEx(0, 0, ICLOUD_DIALOG_CLASS, None)
			while hwnd:
				if hwnd != self._lastHandledHwnd:
					obj = getICloudDialogObject(hwnd)
					if obj:
						self._lastHandledHwnd = hwnd
						log.info(f"iCloudPasswordManager: Detected iCloud dialog hwnd={hwnd}")

						# Check for verification code
						code = findVerificationCode(obj)
						if code:
							# Speak the code digit by digit with spaces for clarity
							spaced_code = " ".join(code)
							log.info(f"iCloudPasswordManager: Announcing code: {code}")
							speech.speakMessage(f"iCloud code: {spaced_code}. {self._repeatHint}")
						else:
							# No code found - this is a password save dialog, focus first button
							log.info(f"iCloudPasswordManager: No code, focusing dialog")
							winUser.setForegroundWindow(hwnd)
							api.setFocusObject(obj)
							eventHandler.queueEvent("gainFocus", obj)
							button = findFirstButton(obj)
							if button:
								log.info(f"iCloudPasswordManager: Focusing button: '{button.name}'")
								api.setFocusObject(button)
								eventHandler.queueEvent("gainFocus", button)
								speech.speakMessage(f"iCloud dialog: {button.name}")
						break
				hwnd = findWindowEx(0, hwnd, ICLOUD_DIALOG_CLASS, None)
		except Exception as e:
			log.error(f"iCloudPasswordManager: Error in timer: {e}")
