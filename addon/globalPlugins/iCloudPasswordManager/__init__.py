# iCloud Password Manager NVDA Add-on
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# This add-on is licensed under the GNU General Public License version 2.

import ctypes
import api
import eventHandler
import globalPluginHandler
import winUser
import wx
from logHandler import log
from NVDAObjects.IAccessible import getNVDAObjectFromEvent

user32 = ctypes.windll.user32

# iCloud dialog identifiers
ICLOUD_DIALOG_CLASS = "#32770"
CHECK_INTERVAL = 500  # milliseconds


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


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin to detect and focus iCloud popups."""

	def __init__(self):
		super().__init__()
		log.info("iCloudPasswordManager: Plugin initialized")
		self._lastHandledHwnd = None
		self._timer = wx.PyTimer(self._checkForICloudDialog)
		self._timer.Start(CHECK_INTERVAL)

	def terminate(self):
		if self._timer:
			self._timer.Stop()
			self._timer = None

	def _checkForICloudDialog(self):
		"""Periodically check for iCloud dialogs and focus them."""
		try:
			hwnd = findWindowEx(0, 0, ICLOUD_DIALOG_CLASS, None)
			while hwnd:
				if hwnd != self._lastHandledHwnd:
					obj = getICloudDialogObject(hwnd)
					if obj:
						self._lastHandledHwnd = hwnd
						log.info(f"iCloudPasswordManager: Focusing iCloud dialog hwnd={hwnd}")
						# Set foreground window
						winUser.setForegroundWindow(hwnd)
						# Set NVDA focus to the object
						api.setFocusObject(obj)
						eventHandler.queueEvent("gainFocus", obj)
						break
				hwnd = findWindowEx(0, hwnd, ICLOUD_DIALOG_CLASS, None)
		except Exception as e:
			log.error(f"iCloudPasswordManager: Error in timer: {e}")
