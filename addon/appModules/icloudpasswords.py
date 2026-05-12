# iCloud Passwords desktop app accessibility (NVDA AppModule)
# Copyright (C) 2024 Stefan Lohmaier <stefan@slohmaier.de>
# Licensed under the GNU General Public License version 2.

import appModuleHandler
import controlTypes
from logHandler import log
from NVDAObjects.UIA import UIA

try:
	from builtins import _
except ImportError:
	def _(x):
		return x


ADD_BUTTON_ID = "m_AddButton"
SORT_BUTTON_ID = "m_SortButton"
CREDENTIALS_LIST_ID = "InternetCredentialsListView"
SHARED_GROUP_LABEL_ID = "m_InternetCredentialSharedGroup"


def _ancestorHasAutomationId(obj, automationId, maxDepth=10):
	"""Walk up the UIA parent chain looking for a given AutomationId."""
	try:
		parent = obj.parent
		for _i in range(maxDepth):
			if parent is None:
				return False
			if getattr(parent, "UIAAutomationId", "") == automationId:
				return True
			parent = parent.parent
	except Exception:
		pass
	return False


def _previousSiblingAutomationId(obj):
	"""Return the UIA AutomationId of the previous sibling, or an empty string."""
	try:
		prev = obj.previous
		if prev is not None:
			return getattr(prev, "UIAAutomationId", "") or ""
	except Exception:
		pass
	return ""


class AddButton(UIA):
	"""Unlabeled '+' button in the iCloud Passwords main window."""

	def _get_name(self):
		return _("Add password")


class SortButton(UIA):
	"""Unlabeled sort button in the iCloud Passwords main window."""

	def _get_name(self):
		return _("Sort")


class ChangeGroupButton(UIA):
	"""Unlabeled chevron button next to the shared-group label on a credential's detail view."""

	def _get_name(self):
		return _("Change group")


class CredentialListItem(UIA):
	"""Row in the saved credentials list. Combines the child TextBlocks into a name."""

	def _get_name(self):
		parts = []
		try:
			for child in self.children:
				if child.role == controlTypes.Role.STATICTEXT:
					text = (child.name or "").strip()
					if text:
						parts.append(text)
		except Exception as e:
			log.debug(f"iCloudPasswords appModule: error reading row children: {e}")
		if parts:
			return ", ".join(parts)
		try:
			return super()._get_name()
		except Exception:
			return ""


class AppModule(appModuleHandler.AppModule):
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if not isinstance(obj, UIA):
			return
		automationId = getattr(obj, "UIAAutomationId", "") or ""
		role = obj.role
		if role == controlTypes.Role.BUTTON:
			if automationId == ADD_BUTTON_ID:
				clsList.insert(0, AddButton)
			elif automationId == SORT_BUTTON_ID:
				clsList.insert(0, SortButton)
			elif not automationId and not (obj.name or ""):
				if _previousSiblingAutomationId(obj) == SHARED_GROUP_LABEL_ID:
					clsList.insert(0, ChangeGroupButton)
		elif role == controlTypes.Role.LISTITEM:
			if _ancestorHasAutomationId(obj, CREDENTIALS_LIST_ID):
				clsList.insert(0, CredentialListItem)
