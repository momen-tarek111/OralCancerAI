import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QStackedWidget
from PySide6.QtCore import Qt, QTimer
from views.splash import SplashScreen


def get_app_dir() -> Path:
    """
    Directory the exe (or script) actually lives in. Used for files that
    must live NEXT TO the exe on disk (e.g. a user database, logs, config),
    regardless of the current working directory the exe was launched from
    (double-click from Explorer, a shortcut with a different "Start in"
    folder, etc).
    """
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built exe
        return Path(sys.executable).resolve().parent
    # Running as a normal .py script
    return Path(__file__).resolve().parent


def get_bundle_dir() -> Path:
    """
    Directory where bundled resources (datas=[...] in the .spec) actually
    live at runtime.

    - ONEFILE build: PyInstaller extracts datas to a temp folder at
      sys._MEIPASS on every launch — NOT next to the exe.
    - ONEDIR build: bundled resources sit next to the exe, same as
      get_app_dir().
    - Plain .py script: same as get_app_dir().
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return get_app_dir()


APP_DIR = get_app_dir()
BUNDLE_DIR = get_bundle_dir()

# ── Step 1: Boot Qt and show splash IMMEDIATELY ───────────────────────────────
app = QApplication(sys.argv)
app.setStyle("Fusion")

splash = SplashScreen()
splash.show()
app.processEvents()  # Force splash to paint RIGHT NOW before any other work


# ── Step 2: Check model weights (fast — just file existence, no imports) ──────
_REQUIRED_MODELS = [
    BUNDLE_DIR / "models/weights/unet_weights2.pth",
    BUNDLE_DIR / "models/weights/best_convnext_4.pth",
    BUNDLE_DIR / "models/weights/best_convnext_5.pth",
    BUNDLE_DIR / "models/weights/best_efficientnet_2.pth",
]

_missing = [str(m) for m in _REQUIRED_MODELS if not m.exists()]

if _missing:
    splash.close()
    missing_list = "\n".join(f"  • {m}" for m in _missing)
    message = (
        "AI model weights not found!\n\n"
        "Missing files:\n"
        f"{missing_list}\n\n"
        "Run this command first:\n"
        "    python setup_models.py\n\n"
        "This downloads the models once (~418 MB).\n"
        "After that, run the app again."
    )

    if getattr(sys, "frozen", False):
        # Frozen + windowed exe has no console — print() is invisible.
        # Show a real message box so the user actually sees the error.
        from PySide6.QtWidgets import QMessageBox
        _err_app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Missing AI Model Weights", message)
    else:
        print()
        print("=" * 55)
        print(message)
        print("=" * 55)
        print()

    sys.exit(1)


# ── AppManager ────────────────────────────────────────────────────────────────
class AppManager(QStackedWidget):
    def __init__(
        self, splash,
        LoginScreen, ChangePasswordScreen, DashboardScreen,
        AddDoctorScreen, AddPatientScreen, PatientsScreen,
        DoctorsScreen, DoctorProfileScreen, MyProfileScreen,
        UpdateDoctorScreen, UpdateMyProfileScreen, ChangeMyPasswordScreen,
        PatientDetailsScreen, ExaminationDetailsScreen, NewExaminationScreen,
        ExaminationReportScreen, QuickCheckScreen,
        initialize_database, hash_password,
    ):
        super().__init__()
        self._hash_password = hash_password

        initialize_database()

        self.setStyleSheet("background-color: #ffffff;")
        self.setWindowTitle("Hidden Truth of Cells")

        # Reuse the splash that is already on screen
        self.splash = splash

        # Build all screens (splash is visible while this runs)
        self.login               = LoginScreen(self)
        self.change_password     = ChangePasswordScreen(self)
        self.dashboard           = DashboardScreen(self)
        self.add_doctor          = AddDoctorScreen(self)
        self.add_patient         = AddPatientScreen(self)
        self.patients            = PatientsScreen(self)
        self.doctors             = DoctorsScreen(self)
        self.doctor_profile      = DoctorProfileScreen(self)
        self.my_profile          = MyProfileScreen(self)
        self.update_doctor       = UpdateDoctorScreen(self)
        self.update_my_profile   = UpdateMyProfileScreen(self)
        self.change_my_password  = ChangeMyPasswordScreen(self)
        self.patient_details     = PatientDetailsScreen(self)
        self.examination_details = ExaminationDetailsScreen(self)
        self.new_examination     = NewExaminationScreen(self)
        self.examination_report  = ExaminationReportScreen(self)
        self.quick_check         = QuickCheckScreen(self)
        self._current_user       = None

        for w in [
            self.login, self.change_password, self.dashboard,
            self.add_doctor, self.add_patient, self.patients,
            self.doctors, self.doctor_profile,
            self.my_profile, self.update_doctor,
            self.update_my_profile, self.change_my_password,
            self.patient_details, self.examination_details,
            self.new_examination, self.examination_report,
            self.quick_check,
        ]:
            self.addWidget(w)

        self._history = ["Dashboard"]
        self._doctor_profile_history = []

        # All screens are built — now start the splash hold timer (500 ms),
        # then fade out and show the main app.
        self.splash.timer.start(500)
        self.splash.timer.timeout.connect(
            lambda: self.splash.fade_out(self.start_main_app)
        )

    # ── Screen list helper ────────────────────────────────────────────────────
    @property
    def _screens(self):
        return [
            self.dashboard, self.add_doctor,
            self.add_patient, self.patients, self.doctors,
            self.doctor_profile, self.my_profile,
            self.update_doctor, self.update_my_profile,
            self.change_my_password, self.patient_details,
            self.examination_details, self.new_examination,
            self.examination_report, self.quick_check,
        ]

    _VALID_PARENTS = {
        "Patients":            {"Dashboard"},
        "Doctors":             {"Dashboard"},
        "Add Patient":         {"Patients", "Dashboard"},
        "Add Doctor":          {"Doctors",  "Dashboard"},
        "Doctor Profile":      {"Doctors"},
        "Update Doctor":       {"Doctor Profile"},
        "My Profile":          {"Dashboard", "Doctors", "Patients", "Doctor Profile"},
        "Update My Profile":   {"My Profile"},
        "Change My Password":  {"My Profile"},
        "Patient Details":     {"Patients"},
        "Examination Details": {"Patient Details", "New Examination"},
        "New Examination":     {"Patient Details"},
        "Examination Report":  {"Examination Details"},
        "Quick Check":         {"Dashboard"},
    }

    # ── Navigation ────────────────────────────────────────────────────────────
    def go_back(self):
        current = self._history[-1] if self._history else "Dashboard"
        parents = self._VALID_PARENTS.get(current, {"Dashboard"})

        for label in reversed(self._history[:-1]):
            if label in parents:
                idx = len(self._history) - 1 - list(
                    reversed(self._history[:-1])).index(label) - 1
                self._history = self._history[:idx + 1]
                self._navigate_silent(label)
                return

        fallback = next(iter(parents))
        self._history = [fallback]
        self._navigate_silent(fallback)

    def _navigate_silent(self, label: str):
        for s in self._screens:
            s.sidebar.set_active(label)
        if label == "Dashboard":
            self.setCurrentWidget(self.dashboard)
            QTimer.singleShot(0, self.dashboard.refresh)
        elif label == "Patients":
            self.patients.refresh()
            self.setCurrentWidget(self.patients)
        elif label == "Add Patient":
            self.setCurrentWidget(self.add_patient)
            QTimer.singleShot(0, self.add_patient.reset_on_enter)
        elif label == "Add Doctor":
            self.setCurrentWidget(self.add_doctor)
            QTimer.singleShot(0, self.add_doctor.reset_on_enter)
        elif label == "Doctors":
            self.doctors.refresh()
            self.setCurrentWidget(self.doctors)
        elif label == "Doctor Profile":
            if hasattr(self.doctor_profile, "_content") and \
               self.doctor_profile._content._user_id:
                self.doctor_profile.load_doctor(
                    self.doctor_profile._content._user_id)
            self.setCurrentWidget(self.doctor_profile)
        elif label == "My Profile":
            self._set_all_avatar_active(True)
            if self._current_user:
                self.my_profile.set_user(self._current_user)
            self.setCurrentWidget(self.my_profile)
        elif label == "Quick Check":
            self.quick_check.reset()
            self.setCurrentWidget(self.quick_check)

    def start_main_app(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        self.setMinimumSize(900, 650)
        self.center_window()
        self.setCurrentWidget(self.login)
        self.show()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.frameGeometry()
        size.moveCenter(screen.center())
        self.move(size.topLeft())

    def login_success(self, user):
        name = user.username
        if not name.lower().startswith("dr"):
            name = f"Dr.{name}"
        for screen in self._screens:
            screen.set_doctor_name(name)
        self._history = ["Dashboard"]
        if user.must_change_password or \
                user.password_hashed == self._hash_password("admin123"):
            self.change_password.set_user(user)
            self.setCurrentWidget(self.change_password)
            QTimer.singleShot(50, lambda: self._apply_user(user))
        else:
            self.setCurrentWidget(self.dashboard)
            QTimer.singleShot(0,  self.dashboard.refresh)
            QTimer.singleShot(50, lambda: self._apply_user(user))

    def _apply_user(self, user):
        self._current_user = user
        for screen in self._screens:
            screen.set_user(user)

    def _set_all_avatar_active(self, active: bool):
        for screen in self._screens:
            if hasattr(screen, "set_avatar_active"):
                screen.set_avatar_active(active)

    def reset_all_sidebars(self):
        for screen in self._screens:
            screen.sidebar._active_label = "Dashboard"
            for name, btn in screen.sidebar._buttons.items():
                btn.blockSignals(True)
                btn.set_active(name == "Dashboard")
                btn.blockSignals(False)
            screen.sidebar.update()

    def navigate_to(self, label: str):
        if not self._history or self._history[-1] != label:
            self._history.append(label)
        for s in self._screens:
            s.sidebar.set_active(label)
        self._set_all_avatar_active(False)
        if label == "Dashboard":
            self.setCurrentWidget(self.dashboard)
            QTimer.singleShot(0, self.dashboard.refresh)
        elif label == "Patients":
            self.patients.refresh()
            self.setCurrentWidget(self.patients)
        elif label == "Add Patient":
            self.setCurrentWidget(self.add_patient)
            QTimer.singleShot(0, self.add_patient.reset_on_enter)
        elif label == "Add Doctor":
            self.setCurrentWidget(self.add_doctor)
            QTimer.singleShot(0, self.add_doctor.reset_on_enter)
        elif label == "Doctors":
            self.doctors.refresh()
            self.setCurrentWidget(self.doctors)
        elif label == "Quick Check":
            QTimer.singleShot(0, self.quick_check.reset)
            self.setCurrentWidget(self.quick_check)

    def navigate_to_my_profile(self):
        if not self._history or self._history[-1] != "My Profile":
            self._history.append("My Profile")
        for s in self._screens:
            s.sidebar.set_active("")
        self._set_all_avatar_active(True)
        if self._current_user:
            self.my_profile.set_user(self._current_user)
        self.setCurrentWidget(self.my_profile)

    def navigate_to_change_password(self):
        if self._current_user:
            self.change_password.set_user(self._current_user)
        self.setCurrentWidget(self.change_password)

    def navigate_to_update_doctor(self, user_id: int):
        for s in self._screens:
            s.sidebar.set_active("")
        self.update_doctor.load_doctor(user_id)
        self.setCurrentWidget(self.update_doctor)

    def navigate_to_update_my_profile(self):
        if not self._current_user:
            return
        if not self._history or self._history[-1] != "Update My Profile":
            self._history.append("Update My Profile")
        for s in self._screens:
            s.sidebar.set_active("")
        self._set_all_avatar_active(False)
        self.update_my_profile.load_doctor(self._current_user.id)
        self.setCurrentWidget(self.update_my_profile)

    def refresh_current_user(self, user_id: int):
        from core.database import SessionLocal
        from models.user import ApplicationUser
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, user_id)
            session.close()
            if not user:
                return
        except Exception as e:
            print(f"refresh_current_user error: {e}")
            return
        self._current_user = user
        name = user.username
        if not name.lower().startswith("dr"):
            name = f"Dr.{name}"
        for screen in self._screens:
            screen.set_doctor_name(name)
            screen.set_user(user)

    def navigate_to_profile(self, user_id: int):
        current_widget = self.currentWidget()
        current_profile_id = None
        if hasattr(self.doctor_profile, "_content"):
            current_profile_id = self.doctor_profile._content._user_id
        if current_widget == self.doctor_profile:
            if current_profile_id and current_profile_id != user_id:
                self._doctor_profile_history.append(current_profile_id)
        elif current_widget != self.update_doctor:
            self._doctor_profile_history.clear()
        if not self._history or self._history[-1] != "Doctor Profile":
            self._history.append("Doctor Profile")
        for s in self._screens:
            s.sidebar.set_active("")
        self._set_all_avatar_active(False)
        self.doctor_profile.load_doctor(user_id)
        self.setCurrentWidget(self.doctor_profile)

    def navigate_to_change_my_password(self):
        if not self._current_user:
            return
        if not self._history or self._history[-1] != "Change My Password":
            self._history.append("Change My Password")
        for s in self._screens:
            s.sidebar.set_active("")
        self._set_all_avatar_active(False)
        self.change_my_password.set_user(self._current_user)
        self.setCurrentWidget(self.change_my_password)

    def navigate_to_patient_details(self, patient_id: int):
        if not self._history or self._history[-1] != "Patient Details":
            self._history.append("Patient Details")
        for s in self._screens:
            s.sidebar.set_active("")
        self._set_all_avatar_active(False)
        self.patient_details.load_patient(patient_id)
        self.setCurrentWidget(self.patient_details)

    def navigate_to_examination_details(self, exam_data: dict, patient_id: int = None):
        if not self._history or self._history[-1] != "Examination Details":
            self._history.append("Examination Details")
        for s in self._screens:
            s.sidebar.set_active("")
        self.examination_details.load_exam(exam_data, patient_id)
        self.setCurrentWidget(self.examination_details)

    def navigate_to_new_examination(self, patient_id: int, patient_name: str):
        if not self._history or self._history[-1] != "New Examination":
            self._history.append("New Examination")
        for s in self._screens:
            s.sidebar.set_active("")
        self.new_examination.set_patient(patient_id, patient_name)
        self.setCurrentWidget(self.new_examination)

    def navigate_to_examination_details_new(self, result: dict):
        if not self._history or self._history[-1] != "Examination Details":
            self._history.append("Examination Details")
        for s in self._screens:
            s.sidebar.set_active("")
        if self._current_user:
            result["doctor_id"] = self._current_user.id
        self.examination_details.load_new_result(result)
        self.setCurrentWidget(self.examination_details)

    def navigate_to_examination_report(self, exam: dict, patient: dict = None,
                                        patient_id: int = None):
        if not self._history or self._history[-1] != "Examination Report":
            self._history.append("Examination Report")
        for s in self._screens:
            s.sidebar.set_active("")
        self.examination_report.load_report(exam, patient, patient_id)
        self.setCurrentWidget(self.examination_report)

    def go_back_from_profile(self):
        if self._doctor_profile_history:
            prev_user_id = self._doctor_profile_history.pop()
            for s in self._screens:
                s.sidebar.set_active("")
            self.doctor_profile.load_doctor(prev_user_id)
            self.setCurrentWidget(self.doctor_profile)
            return
        self.go_back()

    def navigate_to_examination_details_from_report(self):
        if self._history and self._history[-1] == "Examination Report":
            self._history.pop()
        for s in self._screens:
            s.sidebar.set_active("")
        self.setCurrentWidget(self.examination_details)

    navigate_to_examination_details_back = navigate_to_examination_details_from_report


# ── Step 3: Defer ALL heavy imports + app init to next event loop tick ────────
# The splash is already visible on screen. _load_app() runs after Qt processes
# the paint event, so the user sees the splash instantly.
def _load_app():
    from views.login import LoginScreen
    from views.change_password import ChangePasswordScreen
    from views.dashboard import DashboardScreen
    from views.add_doctor import AddDoctorScreen
    from views.add_patient import AddPatientScreen
    from views.patients import PatientsScreen
    from views.doctors import DoctorsScreen
    from views.doctor_profile import DoctorProfileScreen
    from views.my_profile import MyProfileScreen
    from views.update_doctor import UpdateDoctorScreen
    from views.update_my_profile import UpdateMyProfileScreen
    from views.change_my_password import ChangeMyPasswordScreen
    from views.patient_details import PatientDetailsScreen
    from views.examination_details import ExaminationDetailsScreen
    from views.new_examination import NewExaminationScreen
    from views.examination_report import ExaminationReportScreen
    from views.quick_check import QuickCheckScreen
    from core.initializer import initialize_database
    from core.security import hash_password

    manager = AppManager(
        splash,
        LoginScreen, ChangePasswordScreen, DashboardScreen,
        AddDoctorScreen, AddPatientScreen, PatientsScreen,
        DoctorsScreen, DoctorProfileScreen, MyProfileScreen,
        UpdateDoctorScreen, UpdateMyProfileScreen, ChangeMyPasswordScreen,
        PatientDetailsScreen, ExaminationDetailsScreen, NewExaminationScreen,
        ExaminationReportScreen, QuickCheckScreen,
        initialize_database, hash_password,
    )
    # Keep a reference so the garbage collector doesn't destroy the manager
    app._manager = manager


QTimer.singleShot(0, _load_app)  # 0 ms = next event loop tick, splash already painted


if __name__ == "__main__":
    sys.exit(app.exec())