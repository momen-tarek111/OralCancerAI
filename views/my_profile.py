"""
views/my_profile.py
───────────────────
My Profile screen — uses the Doctor Profile layout but with:
- title "My Profile"
- title next to avatar
- two buttons: Update My Information + Change Password
"""

from PySide6.QtWidgets import QSizePolicy

from views.main_layout import MainLayout
from views.doctor_profile import DoctorProfileContent


class MyProfileScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = DoctorProfileContent(mode="my")
        self._content.navigate_back.connect(self._go_back)
        self.set_content(self._content)

    def set_user(self, user):
        super().set_user(user)
        self._content.set_viewer(user)
        # Always load the logged-in user's profile data.
        uid = getattr(user, "id", None)
        if uid:
            self._content.load_doctor(uid)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass

