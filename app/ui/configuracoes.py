from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox
)
from app.memory import carregar_settings, salvar_settings


class DialogoConfiguracoes(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações de Memória")
        self.setMinimumWidth(360)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        cfg = carregar_settings()

        self.inputs = {}
        campos = [
            ("home_goals_offset", "Gols Casa (offset)"),
            ("away_goals_offset", "Gols Visitante (offset)"),
            ("home_team_offset",  "Time Casa (offset)"),
            ("away_team_offset",  "Time Visitante (offset)"),
        ]
        for key, label in campos:
            inp = QLineEdit(hex(cfg.get(key, 0)))
            self.inputs[key] = inp
            form.addRow(label, inp)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._salvar)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _salvar(self):
        novo = {}
        for key, inp in self.inputs.items():
            txt = inp.text().strip()
            try:
                novo[key] = int(txt, 16) if txt.startswith("0x") else int(txt, 16)
            except ValueError:
                QMessageBox.warning(self, "Erro", f"Valor inválido: {txt}")
                return
        salvar_settings(novo)
        self.accept()
