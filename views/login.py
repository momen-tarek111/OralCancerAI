from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon, QAction
from core.database import SessionLocal
from core.utils import resource_path
from models.user import ApplicationUser
from core.security import verify_password

class LoginScreen(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setStyleSheet("background-color: white; border: none;") 

        # --- 1. FLOATING LOGO ---
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
        form_layout.setContentsMargins(40, 30, 40, 40)
        form_layout.setSpacing(10)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF3B30; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)

        form_layout.addWidget(QLabel("Doctor Name"))
        self.username = QLineEdit()
        self.username.setFixedHeight(45)
        self.username.textChanged.connect(self.clear_error_state)
        form_layout.addWidget(self.username)

        form_layout.addSpacing(10)

        form_layout.addWidget(QLabel("Password"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(45)
        self.password.textChanged.connect(self.clear_error_state)
        
        self.toggle_action = QAction(self)
        self.toggle_action.setIcon(QIcon(resource_path("assets/eye_open.png")))
        self.toggle_action.triggered.connect(self.toggle_password_visibility)
        self.password.textChanged.connect(self.update_eye_visibility)
        form_layout.addWidget(self.password)

        form_layout.addSpacing(30)

        self.login_btn = QPushButton("LogIn")
        self.login_btn.setFixedSize(160, 50)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton { background-color: #104EA5; color: white; border-radius: 25px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #1E3658; }
        """)
        self.login_btn.clicked.connect(self.login)
        form_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        center_hbox.addWidget(self.form_card)
        center_hbox.addStretch(1)
        main_layout.addLayout(center_hbox)
        main_layout.addStretch(1) 

    def clear_error_state(self):
        self.error_label.hide()
        for field in [self.username, self.password]:
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
        for field in [self.username, self.password]:
            field.setProperty("error", True)
            field.style().unpolish(field)
            field.style().polish(field)

    def login(self):
        session = SessionLocal()
        try:
            user = session.query(ApplicationUser).filter_by(
                username=self.username.text()
            ).first()

            if user and verify_password(self.password.text(), user.password_hashed):
                # ── Check if account is blocked ───────────────
                if not getattr(user, 'is_active', True):
                    self.show_error("Your account has been blocked by the admin.")
                    return
                self.username.clear()
                self.password.clear()
                self.manager.login_success(user)
            else:
                self.show_error("Invalid Doctor Name or Password")
        finally:
            session.close()

    def update_eye_visibility(self, text):
        if not text:
            self.password.removeAction(self.toggle_action)
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(QIcon(resource_path("assets/eye_open.png")))
        elif self.toggle_action not in self.password.actions():
            self.password.addAction(self.toggle_action, QLineEdit.TrailingPosition)

    def toggle_password_visibility(self):
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setIcon(QIcon(resource_path("assets/eye_closed.png")))
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(QIcon(resource_path("assets/eye_open.png")))