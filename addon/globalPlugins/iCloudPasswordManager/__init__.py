# iCloud Password Manager NVDA Add-on
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# This add-on is licensed under the GNU General Public License version 2.

import ctypes
import re
from ctypes import wintypes

import api
import core
import eventHandler
import globalPluginHandler
import keyboardHandler
import speech
import winUser
from logHandler import log

# iCloud dialog identifiers
ICLOUD_DIALOG_CLASS = "#32770"

# Regex to match verification code (6 digits, possibly with space in middle)
VERIFICATION_CODE_PATTERN = re.compile(r"\b(\d{3})\s?(\d{3})\b")

# Windows event constants
EVENT_OBJECT_SHOW = 0x8002
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

# Callback type for SetWinEventHook
WinEventProcType = ctypes.WINFUNCTYPE(
	None,
	wintypes.HANDLE,  # hWinEventHook
	wintypes.DWORD,  # event
	wintypes.HWND,  # hwnd
	ctypes.c_long,  # idObject
	ctypes.c_long,  # idChild
	wintypes.DWORD,  # dwEventThread
	wintypes.DWORD,  # dwmsEventTime
)


def isICloudDialog(obj):
	"""Check if an NVDA object is an iCloud dialog by searching children."""
	try:
		if not obj or obj.windowClassName != ICLOUD_DIALOG_CLASS:
			return False
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


def isICloudPinField(obj):
	"""Check if an NVDA object is a PIN input field in the iCloud Passwords extension."""
	try:
		# Check for UIA AutomationId like PIN0..PIN5
		automationId = getattr(obj, "UIAAutomationId", "") or ""
		if automationId.startswith("PIN"):
			return True
		# Fallback: check ClassName
		uiaClassName = getattr(obj, "UIAClassName", "") or ""
		if uiaClassName == "PIN":
			return True
		# Fallback: walk parents looking for "iCloud Passwords" document
		if obj.role == 8:  # ROLE_EDITABLETEXT
			parent = obj.parent
			for _ in range(5):
				if parent is None:
					break
				parentName = parent.name or ""
				if parentName == "iCloud Passwords":
					return True
				parent = parent.parent
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error checking PIN field: {e}")
	return False


def sendDigits(code):
	"""Send each digit of the code as a keystroke."""
	for i, digit in enumerate(code):
		core.callLater(50 * i, _sendKey, digit)


def _sendKey(digit):
	"""Send a single digit keystroke."""
	try:
		gesture = keyboardHandler.KeyboardInputGesture.fromName(digit)
		gesture.send()
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error sending key '{digit}': {e}")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to detect and announce iCloud verification codes."""

	def __init__(self):
		super().__init__()
		self._lastHandledHwnd = None
		self._pendingCode = None
		# Must keep reference to prevent garbage collection of the callback
		self._winEventCallback = WinEventProcType(self._onWinEvent)
		# Hook EVENT_OBJECT_SHOW for popup detection
		self._hookShow = ctypes.windll.user32.SetWinEventHook(
			EVENT_OBJECT_SHOW,
			EVENT_OBJECT_SHOW,
			None,
			self._winEventCallback,
			0,  # all processes
			0,  # all threads
			WINEVENT_OUTOFCONTEXT,
		)
		# Hook EVENT_SYSTEM_FOREGROUND as backup
		self._hookForeground = ctypes.windll.user32.SetWinEventHook(
			EVENT_SYSTEM_FOREGROUND,
			EVENT_SYSTEM_FOREGROUND,
			None,
			self._winEventCallback,
			0,
			0,
			WINEVENT_OUTOFCONTEXT,
		)
		log.info(
			f"iCloudPasswordManager: Plugin initialized, hooks: show={self._hookShow} fg={self._hookForeground}"
		)

	def terminate(self):
		if self._hookShow:
			ctypes.windll.user32.UnhookWinEvent(self._hookShow)
		if self._hookForeground:
			ctypes.windll.user32.UnhookWinEvent(self._hookForeground)
		super().terminate()

	def _onWinEvent(self, hook, event, hwnd, idObject, idChild, thread, time):
		"""Raw Windows event callback - runs on NVDA's message pump thread."""
		if not hwnd:
			return
		try:
			className = winUser.getClassName(hwnd)
			if className == ICLOUD_DIALOG_CLASS:
				log.info(f"iCloudPasswordManager: WinEvent {event:#x} for #32770 hwnd={hwnd}")
				core.callLater(100, self._checkWindow, hwnd)
		except Exception:
			pass

	def _checkWindow(self, hwnd):
		"""Check a #32770 window on the main thread."""
		if hwnd == self._lastHandledHwnd:
			return
		try:
			import NVDAObjects.IAccessible

			obj = NVDAObjects.IAccessible.getNVDAObjectFromEvent(hwnd, -4, 0)
			if obj is None:
				return
			log.info(
				f"iCloudPasswordManager: Checking hwnd={hwnd} class={obj.windowClassName} "
				f"children={len(obj.children)}"
			)
			if isICloudDialog(obj):
				self._lastHandledHwnd = hwnd
				log.info(f"iCloudPasswordManager: Confirmed iCloud dialog hwnd={hwnd}")
				self._handleICloudDialog(obj)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error checking window: {e}")

	def event_foreground(self, obj, nextHandler):
		"""Backup: also listen for standard NVDA foreground events."""
		try:
			if obj.windowHandle != self._lastHandledHwnd and isICloudDialog(obj):
				self._lastHandledHwnd = obj.windowHandle
				log.info(f"iCloudPasswordManager: iCloud dialog via event_foreground")
				self._handleICloudDialog(obj)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error in event_foreground: {e}")
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		"""Detect when focus lands on an iCloud PIN field and auto-type the code."""
		try:
			if self._pendingCode and isICloudPinField(obj):
				code = self._pendingCode
				self._pendingCode = None
				log.info(f"iCloudPasswordManager: PIN field focused, auto-typing code: {code}")
				speech.speakMessage(f"Auto-entering iCloud code: {' '.join(code)}")
				# Small delay to ensure the field is ready
				core.callLater(100, sendDigits, code)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error in event_gainFocus: {e}")
		nextHandler()

	def _handleICloudDialog(self, obj):
		"""Handle an iCloud dialog - announce code or focus button."""
		code = findVerificationCode(obj)
		if code:
			spaced_code = " ".join(code)
			log.info(f"iCloudPasswordManager: Announcing code: {code}")
			speech.speakMessage(f"iCloud code: {spaced_code}")
			self._pendingCode = code
			log.info("iCloudPasswordManager: Code stored, waiting for PIN field focus")
		else:
			log.info("iCloudPasswordManager: No code found, focusing dialog")
			button = findFirstButton(obj)
			if button:
				log.info(f"iCloudPasswordManager: Focusing button: '{button.name}'")
				api.setFocusObject(button)
				eventHandler.queueEvent("gainFocus", button)
			else:
				api.setFocusObject(obj)
				eventHandler.queueEvent("gainFocus", obj)
