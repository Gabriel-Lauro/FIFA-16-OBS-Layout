from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
import app.database as db


class DialogoInicio(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FIFA Torneio")
        self.setMinimumSize(480, 320)
        self.torneio_id_selecionado = None
        self.acao = None  # "novo" ou "carregar"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h2>FIFA Torneio</h2>"))

        btn_novo = QPushButton("Novo Torneio")
        btn_novo.clicked.connect(self._novo)
        layout.addWidget(btn_novo)

        layout.addWidget(QLabel("— ou carregar torneio salvo —"))

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self._carregar)
        layout.addWidget(self.lista)

        btn_carregar = QPushButton("Carregar Selecionado")
        btn_carregar.clicked.connect(self._carregar)
        layout.addWidget(btn_carregar)

        self._popular_lista()

    def _popular_lista(self):
        self.lista.clear()
        for t in db.listar_torneios():
            item = QListWidgetItem(f"{t['nome']}  [{t['formato']} times] — {t['status']}")
            item.setData(Qt.UserRole, t["id"])
            self.lista.addItem(item)

    def _novo(self):
        self.acao = "novo"
        self.accept()

    def _carregar(self):
        item = self.lista.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um torneio.")
            return
        self.torneio_id_selecionado = item.data(Qt.UserRole)
        self.acao = "carregar"
        self.accept()
