from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QAbstractItemView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QColor, QBrush
from app.models import Torneio, Jogo, StatusJogo
from app.state import EstadoTorneio

# cores que funcionam tanto em tema claro quanto escuro (apenas o texto muda)
COR_ANDAMENTO = QColor("#f0a500")   # amarelo/laranja
COR_ENCERRADO = QColor("#4caf50")   # verde


class Sinais(QObject):
    atualizar = Signal()


class MainWindow(QMainWindow):
    def __init__(self, torneio: Torneio, estado: EstadoTorneio, on_iniciar_jogo, on_interromper, on_editar_jogo):
        super().__init__()
        self.torneio = torneio
        self.estado = estado
        self.on_iniciar_jogo = on_iniciar_jogo
        self.on_interromper = on_interromper
        self.on_editar_jogo = on_editar_jogo
        self._sinais = Sinais()
        self._sinais.atualizar.connect(self._atualizar_tabela)

        self.setWindowTitle(f"Torneio — {torneio.nome}")
        self.setMinimumSize(960, 600)
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        topo = QHBoxLayout()
        topo.addWidget(QLabel(f"<b>{self.torneio.nome}</b>  [{self.torneio.formato.value} times]"))
        topo.addStretch()

        self.btn_interromper = QPushButton("Interromper jogo em andamento")
        self.btn_interromper.setEnabled(False)
        self.btn_interromper.clicked.connect(self._interromper)
        topo.addWidget(self.btn_interromper)
        layout.addLayout(topo)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(7)
        self.tabela.setHorizontalHeaderLabels([
            "Fase", "Rodada", "Time 1 (Jogador)", "Placar", "Time 2 (Jogador)", "Status", "Ação"
        ])
        hh = self.tabela.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tabela.setColumnWidth(6, 100)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        layout.addWidget(self.tabela)

        self._atualizar_tabela()

    def _todos_jogos(self) -> list[Jogo]:
        jogos = []
        for g in self.torneio.grupos:
            jogos.extend(g.jogos)
        jogos.extend(self.torneio.jogos_matamata)
        return sorted(jogos, key=lambda j: (
            0 if j.fase == "grupos" else 1,
            j.rodada,
            j.id or 0
        ))

    def _atualizar_tabela(self):
        jogos = self._todos_jogos()
        self.tabela.setRowCount(len(jogos))

        jogo_em_andamento = self.estado.get_jogo_atual()
        self.btn_interromper.setEnabled(jogo_em_andamento is not None)

        for row, j in enumerate(jogos):
            fase_label = j.fase.capitalize()
            if j.fase == "grupos":
                grupo_nome = next(
                    (g.nome for g in self.torneio.grupos if g.id == j.id_grupo), "?"
                )
                fase_label = f"Grupo {grupo_nome}"

            jog1 = f"\n({j.time1.nome_jogador})" if j.time1.nome_jogador else ""
            jog2 = f"\n({j.time2.nome_jogador})" if j.time2.nome_jogador else ""

            if j.gols1 is not None and j.gols2 is not None:
                placar = f"{j.gols1} – {j.gols2}"
            else:
                placar = "vs"

            # cor do texto de status — sem alterar o fundo da linha
            if j.status == StatusJogo.EM_ANDAMENTO:
                status_txt = "em andamento"
                status_cor = COR_ANDAMENTO
            elif j.status == StatusJogo.ENCERRADO:
                status_txt = "encerrado"
                status_cor = COR_ENCERRADO
            else:
                status_txt = "pendente"
                status_cor = None

            celulas = [
                fase_label,
                str(j.rodada),
                f"{j.time1.nome_time}{jog1}",
                placar,
                f"{j.time2.nome_time}{jog2}",
                status_txt,
            ]

            for col, txt in enumerate(celulas):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                # colore apenas a célula de status
                if col == 5 and status_cor:
                    item.setForeground(QBrush(status_cor))
                self.tabela.setItem(row, col, item)

            # coluna de ação
            if j.status == StatusJogo.PENDENTE and jogo_em_andamento is None:
                btn = QPushButton("Iniciar")
                btn.clicked.connect(lambda _, jogo=j: self.on_iniciar_jogo(jogo))
                self.tabela.setCellWidget(row, 6, btn)
            elif j.status == StatusJogo.EM_ANDAMENTO:
                btn = QPushButton("Gerenciar")
                btn.clicked.connect(lambda _, jogo=j: self.on_iniciar_jogo(jogo))
                self.tabela.setCellWidget(row, 6, btn)
            elif j.status == StatusJogo.ENCERRADO:
                btn = QPushButton("Editar")
                btn.clicked.connect(lambda _, jogo=j: self.on_editar_jogo(jogo))
                self.tabela.setCellWidget(row, 6, btn)
            else:
                self.tabela.setCellWidget(row, 6, None)

        self.tabela.resizeRowsToContents()

    def _interromper(self):
        jogo = self.estado.get_jogo_atual()
        if not jogo:
            return
        resp = QMessageBox.question(
            self, "Interromper",
            f"Interromper {jogo.time1.nome_time} vs {jogo.time2.nome_time}?\n"
            "O resultado não será registrado.",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self.on_interromper()

    def atualizar(self):
        self._sinais.atualizar.emit()
