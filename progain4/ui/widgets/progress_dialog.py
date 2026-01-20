from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ProgressDialog(QDialog):
    """
    Ventana de progreso moderna para mostrar el proceso de generación de PDF.
    """
    
    def __init__(self, parent=None, total_steps=100):
        super().__init__(parent)
        self.total_steps = total_steps
        self.current_step = 0
        
        self.setWindowTitle("Generando PDF...")
        self.setModal(True)
        self.setFixedSize(450, 180)
        
        # Deshabilitar botón de cerrar
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint
        )
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Card contenedor
        card = QFrame()
        card.setObjectName("progressCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout. setSpacing(10)
        
        # Título
        self.title_label = QLabel("Preparando reporte...")
        self.title_label.setObjectName("progressTitle")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label. setFont(title_font)
        card_layout.addWidget(self.title_label)
        
        # Mensaje de estado
        self.status_label = QLabel("Inicializando...")
        self.status_label.setObjectName("progressStatus")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self. status_label)
        
        # Barra de progreso
        self. progress_bar = QProgressBar()
        self.progress_bar. setMinimum(0)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        card_layout.addWidget(self. progress_bar)
        
        # Detalle actual
        self.detail_label = QLabel("")
        self.detail_label. setObjectName("progressDetail")
        self.detail_label.setWordWrap(True)
        card_layout.addWidget(self.detail_label)
        
        layout.addWidget(card)
        
        # Estilos
        self.setStyleSheet("""
            QDialog {
                background-color: #F9FAFB;
            }
            QFrame#progressCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            QLabel#progressTitle {
                color: #111827;
            }
            QLabel#progressStatus {
                color: #6B7280;
                font-size: 10px;
            }
            QLabel#progressDetail {
                color: #9CA3AF;
                font-size: 9px;
                font-style: italic;
            }
            QProgressBar {
                border:  1px solid #D1D5DB;
                border-radius: 6px;
                text-align:  center;
                background-color: #F3F4F6;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 5px;
            }
        """)
    
    def update_progress(self, step, status_text, detail_text=""):
        """
        Actualiza el progreso. 
        
        Args:
            step:  Paso actual (0 a total_steps)
            status_text:  Texto principal de estado
            detail_text:  Texto de detalle (opcional)
        """
        self.current_step = step
        self.progress_bar.setValue(step)
        self.status_label.setText(status_text)
        
        if detail_text:
            self.detail_label.setText(detail_text)
        else:
            self.detail_label. setText("")
        
        # Forzar actualización de UI
        self.repaint()
        QApplication.processEvents()
    
    def set_title(self, title):
        """Cambia el título de la ventana."""
        self.title_label.setText(title)
    
    def finish(self):
        """Cierra la ventana de progreso."""
        self.accept()


# Importar QApplication para processEvents
from PyQt6.QtWidgets import QApplication