from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject
from app.models import Jogo, StatusJogo
from app.state import EstadoTorneio


class Sinais(QObject):
    placar_atualizado = Signal(int, int)
    conexao_atualizada = Signal(bool)


class AdminWindow(QDialog):
    def __init__(self, jogo: Jogo, estado: EstadoTorneio, parent=None):
        super().__init__(parent)
        self.jogo = jogo
        self.estado = estado
        self._sinais = Sinais()
        self._sinais.placar_atualizado.connect(self._on_placar)
        self._sinais.conexao_atualizada.connect(self._on_conexao)

        self.setWindowTitle("Partida em Andamento")
        self.setMinimumSize(420, 300)
        self.setModal(False)
        self._build()

        # registra callbacks (thread-safe → emit signal)
        estado.on_placar(lambda g1, g2: self._sinais.placar_atualizado.emit(g1, g2))
        estado.on_conexao(lambda c: self._sinais.conexao_atualizada.emit(c))

        self._atualizar_conexao(estado.get_fifa_conectado())

    def _build(self):
        layout = QVBoxLayout(self)

        # times
        times_row = QHBoxLayout()
        self.lbl_time1 = QLabel(self._label_time(self.jogo.time1))
        self.lbl_time1.setAlignment(Qt.AlignCenter)
        self.lbl_placar = QLabel("0 — 0")
        self.lbl_placar.setAlignment(Qt.AlignCenter)
        font = self.lbl_placar.font()
        font.setPointSize(28)
        font.setBold(True)
        self.lbl_placar.setFont(font)
        self.lbl_time2 = QLabel(self._label_time(self.jogo.time2))
        self.lbl_time2.setAlignment(Qt.AlignCenter)
        times_row.addWidget(self.lbl_time1, 2)
        times_row.addWidget(self.lbl_placar, 1)
        times_row.addWidget(self.lbl_time2, 2)
        layout.addLayout(times_row)

        # status FIFA
        self.lbl_conexao = QLabel("")
        self.lbl_conexao.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_conexao)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # correção manual
        layout.addWidget(QLabel("Correção manual de placar:"))
        corr = QHBoxLayout()
        self.spin1 = QSpinBox()
        self.spin1.setRange(0, 20)
        self.spin2 = QSpinBox()
        self.spin2.setRange(0, 20)
        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(self._aplicar_correcao)
        corr.addWidget(QLabel(self.jogo.time1.nome_time))
        corr.addWidget(self.spin1)
        corr.addWidget(QLabel("×"))
        corr.addWidget(self.spin2)
        corr.addWidget(QLabel(self.jogo.time2.nome_time))
        corr.addWidget(btn_aplicar)
        layout.addLayout(corr)

        layout.addStretch()

        # encerrar
        self.btn_encerrar = QPushButton("Encerrar Jogo")
        self.btn_encerrar.clicked.connect(self._encerrar)
        layout.addWidget(self.btn_encerrar)

    def _label_time(self, time) -> str:
        jog = f"\n{time.nome_jogador}" if time.nome_jogador else ""
        return f"{time.nome_time}{jog}"

    def _on_placar(self, g1: int, g2: int):
        self.lbl_placar.setText(f"{g1} — {g2}")
        self.spin1.setValue(g1)
        self.spin2.setValue(g2)

    def _on_conexao(self, conectado: bool):
        self._atualizar_conexao(conectado)

    def _atualizar_conexao(self, conectado: bool):
        if conectado:
            self.lbl_conexao.setText("FIFA 16: conectado")
            self.lbl_conexao.setStyleSheet("color: green;")
        else:
            self.lbl_conexao.setText("Aguardando FIFA 16...")
            self.lbl_conexao.setStyleSheet("color: orange;")

    def _aplicar_correcao(self):
        g1 = self.spin1.value()
        g2 = self.spin2.value()
        self.estado.atualizar_placar(g1, g2)

    def _encerrar(self):
        g1, g2 = self.estado.get_placar()
        
        if self.jogo.fase != "grupos" and g1 == g2:
            QMessageBox.warning(
                self, "Placar inválido",
                "Jogos de mata-mata não podem terminar empatados.\n"
                "Corrija o placar antes de encerrar."
            )
            return
        
        resp = QMessageBox.question(
            self, "Encerrar",
            f"Encerrar com placar {g1} × {g2}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self.accept()
