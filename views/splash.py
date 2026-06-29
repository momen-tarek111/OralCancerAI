from PySide6.QtWidgets import QWidget, QLabel, QFrame, QApplication, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont, QLinearGradient, QPalette, QBrush, QColor

from core.utils import resource_path

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        # 1. HIDE NAV BAR & FLAGS
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(900, 550)

        # Main White Container
        self.container = QFrame(self)
        self.container.setFixedSize(900, 550)
        self.container.setStyleSheet("background-color: white; border-radius: 20px;")

        # Logo
        self.logo_label = QLabel(self.container)
        pixmap = QPixmap(resource_path("assets/logo.png"))
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setFixedSize(900, 420) 
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.move(0, 30)

        # --- 2. TEXT WITH GRADIENT, ABORETO FONT & FIGMA SHADOW ---
        self.text_label = QLabel("HIDDEN TRUTH\nOF CELLS", self.container)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFixedWidth(900)
        self.text_label.move(40, 315) # Positioned in the "Green Area"

        # Figma Font: Aboreto, 36px, Weight 400
        font = QFont("Aboreto", 16)
        font.setWeight(QFont.Weight.Normal) 
        self.text_label.setFont(font)

        # Figma Gradient: #104EA5 to #7CA7E3
        gradient = QLinearGradient(0, 0, 900, 0) 
        gradient.setColorAt(0.0, QColor("#104EA5"))
        gradient.setColorAt(1.0, QColor("#7CA7E3"))

        palette = self.text_label.palette()
        palette.setBrush(QPalette.WindowText, QBrush(gradient))
        self.text_label.setPalette(palette)

        # --- FIGMA BOX-SHADOW IMPLEMENTATION ---
        # box-shadow: 0px (X) 4px (Y) 4px (Blur) 0px (Spread) #00000040 (Color)
        figma_shadow = QGraphicsDropShadowEffect(self)
        figma_shadow.setBlurRadius(4)           # 4px Blur
        figma_shadow.setXOffset(0)              # 0px X
        figma_shadow.setYOffset(4)              # 4px Y
        # #00000040: The '40' in hex is 64 in decimal alpha (approx 25% opacity)
        figma_shadow.setColor(QColor(0, 0, 0, 64)) 
        
        self.text_label.setGraphicsEffect(figma_shadow)
        
        # Ensure the label box is invisible so shadow only hits the letters
        self.text_label.setStyleSheet("background: transparent; border: none;")

        # 3. CENTER & TIMER
        self.center_on_screen()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.start(1000)

    def center_on_screen(self):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x = (screen_geo.width() - self.width()) // 2
        y = (screen_geo.height() - self.height()) // 2
        self.move(x, y)

    def fade_out(self, callback):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(callback)
        self.animation.finished.connect(self.close)
        self.animation.start()