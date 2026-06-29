from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon, QAction
from core.database import SessionLocal
from core.security import hash_password
from core.utils import resource_path

class ChangePasswordScreen(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.user = None
        self.setStyleSheet("background-color: white; border: none;") 

        # --- 1. FLOATING LOGO (Matching Login) ---
        self.logo_container = QWidget(self)
        self.logo_container.setFixedSize(120, 120)
        self.logo_container.move(10, 10)
        
        logo_icon = QLabel(self.logo_container)
        pixmap = QPixmap(resource_path("assets/logo.png"))
        if not pixmap.isNull():
            logo_icon.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_icon.setGeometry(0, 0, 60, 60) 
        
        logo_text = QLabel("HIDDEN TRUTH\nOF CELLS", self.logo_container)
        logo_text.setAlignment(Qt.AlignCenter)
        logo_text.setStyleSheet("color: #104EA5; font-weight: bold; font-size: 8px; background: transparent;")
        logo_text.setFixedWidth(120)
        logo_text.move(-5, 45)

        # --- 2. LAYOUT ---
        main_layout = QVBoxLayout(self)
        main_layout.addStretch(1) 

        center_hbox = QHBoxLayout()
        center_hbox.addStretch(1)

        self.form_card = QFrame()
        self.form_card.setFixedWidth(400) 
        self.form_card.setStyleSheet("""
            QFrame { background-color: rgba(230, 241, 255, 148); border-radius: 25px; }
            QLabel { background: transparent; color: #104EA5; font-size: 16px; font-weight: 500; }
            
            QLineEdit { 
                border: 1px solid #104EA5; 
                border-radius: 12px; 
                background: white; 
                padding-left: 12px; 
                color: black; 
            }
            QLineEdit[error="true"] { 
                border: 2px solid #FF3B30; 
            }
        """)

        form_layout = QVBoxLayout(self.form_card)
        form_layout.setContentsMargins(40, 20, 40, 40)
        form_layout.setSpacing(10)

        # Header Title
        header = QLabel("Change your password !")
        header.setStyleSheet("color: #D4E157; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(header)

        # --- ERROR MESSAGE LABEL ---
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF3B30; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)

        # New Password
        form_layout.addWidget(QLabel("New Password"))
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setFixedHeight(45)
        self.new_password.textChanged.connect(self.clear_error_state)
        
        self.toggle_new = QAction(self)
        self.toggle_new.setIcon(QIcon(resource_path("assets/eye_open.png")))
        self.toggle_new.triggered.connect(lambda: self.toggle_visibility(self.new_password, self.toggle_new))
        self.new_password.textChanged.connect(lambda: self.update_eye_visibility(self.new_password, self.toggle_new))
        form_layout.addWidget(self.new_password)

        form_layout.addSpacing(10)

        # Confirm Password
        form_layout.addWidget(QLabel("Confirm Password"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setFixedHeight(45)
        self.confirm_password.textChanged.connect(self.clear_error_state)

        self.toggle_confirm = QAction(self)
        self.toggle_confirm.setIcon(QIcon(resource_path("assets/eye_open.png")))
        self.toggle_confirm.triggered.connect(lambda: self.toggle_visibility(self.confirm_password, self.toggle_confirm))
        self.confirm_password.textChanged.connect(lambda: self.update_eye_visibility(self.confirm_password, self.toggle_confirm))
        form_layout.addWidget(self.confirm_password)

        form_layout.addSpacing(30)

        # Confirm Button
        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setFixedSize(160, 50)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setStyleSheet("""
            QPushButton { background-color: #104EA5; color: white; border-radius: 25px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #1E3658; }
        """)
        self.confirm_btn.clicked.connect(self.handle_change_password)
        form_layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)

        center_hbox.addWidget(self.form_card)
        center_hbox.addStretch(1)
        main_layout.addLayout(center_hbox)
        main_layout.addStretch(1) 

    # --- LOGIC ---

    def set_user(self, user):
        self.user = user

    def reset_fields(self):
        """Clear all fields and reset error state."""
        self.new_password.clear()
        self.confirm_password.clear()
        # Reset echo mode to password in case eye was toggled
        self.new_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setEchoMode(QLineEdit.Password)
        # Reset eye icons
        self.toggle_new.setIcon(QIcon(resource_path("assets/eye_open.png")))
        self.toggle_confirm.setIcon(QIcon(resource_path("assets/eye_open.png")))
        # Remove eye actions
        self.new_password.removeAction(self.toggle_new)
        self.confirm_password.removeAction(self.toggle_confirm)
        # Hide error
        self.clear_error_state()

    def clear_error_state(self):
        self.error_label.hide()
        for field in [self.new_password, self.confirm_password]:
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
        for field in [self.new_password, self.confirm_password]:
            field.setProperty("error", True)
            field.style().unpolish(field)
            field.style().polish(field)

    def update_eye_visibility(self, field, action):
        if not field.text():
            field.removeAction(action)
            field.setEchoMode(QLineEdit.Password)
            action.setIcon(QIcon(resource_path("assets/eye_open.png")))
        elif action not in field.actions():
            field.addAction(action, QLineEdit.TrailingPosition)

    def toggle_visibility(self, field, action):
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            action.setIcon(QIcon(resource_path("assets/eye_closed.png")))
        else:
            field.setEchoMode(QLineEdit.Password)
            action.setIcon(QIcon(resource_path("assets/eye_open.png")))

    def handle_change_password(self):
        # Validation
        if not self.new_password.text() or not self.confirm_password.text():
            self.show_error("Fields cannot be empty")
            return
            
        if self.new_password.text() != self.confirm_password.text():
            self.show_error("Passwords do not match")
            return

        # Database Update
        session = SessionLocal()
        try:
            db_user = session.get(type(self.user), self.user.id)
            db_user.password_hashed      = hash_password(self.new_password.text())
            db_user.must_change_password = False
            session.commit()
            # Reset fields before transitioning
            self.reset_fields()
            # Transition to dashboard after success
            self.manager.setCurrentWidget(self.manager.dashboard)
        except Exception as e:
            print(e)
            self.show_error(str(e))
        finally:
            session.close()