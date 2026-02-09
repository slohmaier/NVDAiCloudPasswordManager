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
EVENT_OBJECT_FOCUS = 0x8005
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


def _getCredentialListSelectedItem():
	"""Use UIA to find the currently active item in the iCloud credential list.

	Chrome's UIA provider blocks child traversal on the credentialList element,
	so we search for ListItem elements directly from the window element and check
	their className for "active" (set by Chrome when an item is arrow-key selected).
	"""
	try:
		import UIAHandler

		uia = UIAHandler.handler
		if not uia or not uia.clientObject:
			return None
		focusObj = api.getFocusObject()
		if not focusObj:
			return None
		hwnd = focusObj.windowHandle
		if not hwnd:
			return None
		windowElement = uia.clientObject.elementFromHandle(hwnd)
		if not windowElement:
			return None
		# Search for ListItem elements (controlType 50007) in the window
		listItemCondition = uia.clientObject.CreatePropertyCondition(30003, 50007)  # UIA_ControlTypePropertyId
		allItems = windowElement.FindAll(4, listItemCondition)  # TreeScope_Descendants
		if not allItems or allItems.length == 0:
			return None
		for i in range(allItems.length):
			item = allItems.getElement(i)
			if not item:
				continue
			className = item.currentClassName or ""
			# Only consider iCloud credential items
			if (
				"credential" not in className
				and "iCloudPasswords" not in className
				and "password-manager" not in className
			):
				continue
			# The active/selected item gets "active" appended to its className
			clsLower = className.lower()
			if "active" in clsLower or "selected" in clsLower or "focused" in clsLower:
				name = item.currentName or ""
				label = _readUIAChildTextsViaFindAll(item, uia) or name
				return label
	except Exception as e:
		log.debug(f"iCloudPasswordManager: Error getting credential selection: {e}")
	return None


def _readUIAChildTextsViaFindAll(element, uia):
	"""Read text from child UIA elements using FindAll (avoids tree walker E_POINTER issues)."""
	try:
		trueCondition = uia.clientObject.CreateTrueCondition()
		children = element.FindAll(2, trueCondition)  # TreeScope_Children
		if not children:
			return None
		parts = []
		for i in range(children.length):
			child = children.getElement(i)
			if child:
				name = child.currentName or ""
				if name:
					parts.append(name)
		return ", ".join(parts) if parts else None
	except Exception:
		# Fallback: try the element's own name
		try:
			return element.currentName or None
		except Exception:
			return None


def _filterSpeechForCredentialList(speechSequence):
	"""Filter speech to replace 'blank' with credential list item text."""
	blankText = _("blank")
	hasBlank = False
	for item in speechSequence:
		if isinstance(item, str) and (item == blankText or item.lower() == "blank" or item.lower() == "leer"):
			hasBlank = True
			break
	if not hasBlank:
		return speechSequence
	# Check if focus is in Edge/Chrome (where credential popups appear)
	try:
		focusObj = api.getFocusObject()
		if not focusObj or focusObj.windowClassName not in (
			"Chrome_RenderWidgetHostHWND", "Chrome_WidgetWin_1"
		):
			return speechSequence
	except Exception:
		return speechSequence
	# Try to get the selected credential item
	label = _getCredentialListSelectedItem()
	if not label:
		return speechSequence
	# Replace "blank" with the credential label
	newSequence = []
	for item in speechSequence:
		if isinstance(item, str) and (item == blankText or item.lower() == "blank" or item.lower() == "leer"):
			newSequence.append(label)
		else:
			newSequence.append(item)
	return newSequence


# Need gettext for matching translated "blank" string
try:
	from builtins import _
except ImportError:
	def _(x):
		return x


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to make iCloud Password Manager popups accessible."""

	def __init__(self):
		super().__init__()
		self._lastHandledHwnd = None
		self._pendingCode = None
		# Register speech filter for credential list "blank" replacement
		from speech.extensions import filter_speechSequence

		filter_speechSequence.register(_filterSpeechForCredentialList)
		# Must keep reference to prevent garbage collection of the callback
		self._winEventCallback = WinEventProcType(self._onWinEvent)
		# Hook EVENT_OBJECT_SHOW for iCloud popup detection
		self._hookShow = ctypes.windll.user32.SetWinEventHook(
			EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW,
			None, self._winEventCallback, 0, 0, WINEVENT_OUTOFCONTEXT,
		)
		# Hook EVENT_SYSTEM_FOREGROUND as backup for popup detection
		self._hookForeground = ctypes.windll.user32.SetWinEventHook(
			EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
			None, self._winEventCallback, 0, 0, WINEVENT_OUTOFCONTEXT,
		)
		# Hook EVENT_OBJECT_FOCUS for Edge extension PIN field detection
		self._hookFocus = ctypes.windll.user32.SetWinEventHook(
			EVENT_OBJECT_FOCUS, EVENT_OBJECT_FOCUS,
			None, self._winEventCallback, 0, 0, WINEVENT_OUTOFCONTEXT,
		)
		log.info("iCloudPasswordManager: Plugin initialized")

	def terminate(self):
		from speech.extensions import filter_speechSequence

		filter_speechSequence.unregister(_filterSpeechForCredentialList)
		for hook in (self._hookShow, self._hookForeground, self._hookFocus):
			if hook:
				ctypes.windll.user32.UnhookWinEvent(hook)
		super().terminate()

	def _onWinEvent(self, hook, event, hwnd, idObject, idChild, thread, time):
		"""Raw Windows event callback - runs on NVDA's message pump thread."""
		if not hwnd:
			return
		try:
			className = winUser.getClassName(hwnd)
			if className == ICLOUD_DIALOG_CLASS and event in (EVENT_OBJECT_SHOW, EVENT_SYSTEM_FOREGROUND):
				core.callLater(100, self._checkWindow, hwnd)
			elif event == EVENT_OBJECT_FOCUS and className in (
				"Chrome_WidgetWin_1", "Chrome_RenderWidgetHostHWND"
			):
				core.callLater(50, self._checkFocusedUIA)
		except Exception:
			pass

	def _checkFocusedUIA(self):
		"""Check the UIA focused element for iCloud PIN fields (auto-type verification code)."""
		if not self._pendingCode:
			return
		try:
			import UIAHandler

			uia = UIAHandler.handler
			if not uia or not uia.clientObject:
				return
			focused = uia.clientObject.getFocusedElement()
			if not focused:
				return
			className = focused.currentClassName or ""
			automationId = focused.currentAutomationId or ""
			if automationId.startswith("PIN") or className == "PIN":
				code = self._pendingCode
				self._pendingCode = None
				log.info(f"iCloudPasswordManager: PIN field focused via UIA, auto-typing: {code}")
				speech.speakMessage(f"Auto-entering iCloud code: {' '.join(code)}")
				core.callLater(100, sendDigits, code)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error checking UIA focus: {e}")

	def _checkWindow(self, hwnd):
		"""Check a #32770 window on the main thread."""
		if hwnd == self._lastHandledHwnd:
			return
		try:
			import NVDAObjects.IAccessible

			obj = NVDAObjects.IAccessible.getNVDAObjectFromEvent(hwnd, -4, 0)
			if obj is None:
				return
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
				self._handleICloudDialog(obj)
		except Exception as e:
			log.debug(f"iCloudPasswordManager: Error in event_foreground: {e}")
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		"""Detect iCloud PIN fields on focus for auto-typing verification codes."""
		try:
			if self._pendingCode and isICloudPinField(obj):
				code = self._pendingCode
				self._pendingCode = None
				log.info(f"iCloudPasswordManager: PIN field focused, auto-typing code: {code}")
				speech.speakMessage(f"Auto-entering iCloud code: {' '.join(code)}")
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
		else:
			log.info("iCloudPasswordManager: No code found, focusing dialog")
			button = findFirstButton(obj)
			if button:
				api.setFocusObject(button)
				eventHandler.queueEvent("gainFocus", button)
			else:
				api.setFocusObject(obj)
				eventHandler.queueEvent("gainFocus", obj)
