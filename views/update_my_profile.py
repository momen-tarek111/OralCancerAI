"""
views/update_my_profile.py
──────────────────────────
Update My Profile screen — identical form to Update Doctor but:
  * back button label  →  "< Update My Profile"
  * card title label   →  "Update My Profile"
  * cancel / success   →  navigates to My Profile, not Doctor Profile
  * on success         →  refreshes _current_user so sidebar updates instantly
Parent screen: My Profile
"""

from views.main_layout import MainLayout
from views.update_doctor import UpdateDoctorContent


# ─────────────────────────────────────────────────────────────
#  CONTENT  (thin subclass — only navigation + labels differ)
# ─────────────────────────────────────────────────────────────
class UpdateMyProfileContent(UpdateDoctorContent):

    def _build_ui(self):
        super()._build_ui()

        # ── Fix back-button label ─────────────────────────────
        try:
            outer_layout = self.layout()           # QVBoxLayout
            back_row     = outer_layout.itemAt(0)  # first item → QHBoxLayout
            if back_row and back_row.layout():
                btn_item = back_row.layout().itemAt(0)
                if btn_item and btn_item.widget():
                    btn_item.widget().setText("< Update My Profile")
        except Exception:
            pass

        # ── Fix card title label ("Update Doctor" → "Update My Profile") ─
        # Structure: outer[1] = card (QFrame)
        #   card layout[0] = form_frame (QFrame)
        #     form layout[0] = top_row (QHBoxLayout)
        #       top_row[0] = avatar_col (QVBoxLayout)
        #       top_row[1] = title_col (QVBoxLayout)
        #         title_col[0] = title_lbl (QLabel)
        try:
            outer_layout  = self.layout()
            card_item     = outer_layout.itemAt(1)        # white card
            card_widget   = card_item.widget() if card_item else None
            if card_widget:
                card_vl   = card_widget.layout()
                form_item = card_vl.itemAt(0)             # form_frame
                form_w    = form_item.widget() if form_item else None
                if form_w:
                    form_vl   = form_w.layout()
                    top_item  = form_vl.itemAt(0)         # top_row QHBoxLayout
                    top_row   = top_item.layout() if top_item else None
                    if top_row:
                        title_col_item = top_row.itemAt(1)    # title_col QVBoxLayout
                        title_col      = title_col_item.layout() if title_col_item else None
                        if title_col:
                            lbl_item = title_col.itemAt(0)    # QLabel
                            lbl      = lbl_item.widget() if lbl_item else None
                            if lbl:
                                lbl.setText("Update My Profile")
        except Exception:
            pass   # cosmetic — never crash

    # ── override navigation so everything goes to My Profile ─
    def _cancel(self):
        if self._manager_ref and hasattr(self._manager_ref, "navigate_to_my_profile"):
            self._manager_ref.navigate_to_my_profile()
        else:
            self.go_back_signal.emit()

    def _go_to_profile(self):
        """After a successful save, reload the current user so the
        sidebar visibility reflects any role change, then go to My Profile."""
        if self._manager_ref:
            # Re-read the user from the DB so role / image are fresh.
            if hasattr(self._manager_ref, "refresh_current_user"):
                self._manager_ref.refresh_current_user(self._user_id)
            if hasattr(self._manager_ref, "navigate_to_my_profile"):
                self._manager_ref.navigate_to_my_profile()


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class UpdateMyProfileScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = UpdateMyProfileContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def load_doctor(self, user_id: int):
        self._content.load_doctor(user_id)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "navigate_to_my_profile"):
            self._manager.navigate_to_my_profile()
        elif self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass