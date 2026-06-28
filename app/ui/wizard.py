import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QScrollArea, QMessageBox,
    QCheckBox, QFrame
)
from PySide6.QtCore import Qt
from app.models import Formato, Time, Torneio, Grupo
from app.times import TEAM_IDS
from app import engine


FORMATOS = [16, 32]


class WizardNovoTorneio(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Torneio")
        self.setMinimumSize(600, 500)

        self.nome = ""
        self.formato = Formato.F32
        self.times_selecionados: list[Time] = []   # Time com nome_jogador
        self.grupos: list[Grupo] = []
        self.jogos_matamata = []

        self._build()

    def _build(self):
        root = QVBoxLayout(self)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.stack.addWidget(self._passo1())
        self.stack.addWidget(self._passo2())
        self.stack.addWidget(self._passo3())
        self.stack.addWidget(self._passo4())

        nav = QHBoxLayout()
        self.btn_voltar = QPushButton("Voltar")
        self.btn_voltar.clicked.connect(self._voltar)
        self.btn_avancar = QPushButton("Avançar")
        self.btn_avancar.clicked.connect(self._avancar)
        nav.addWidget(self.btn_voltar)
        nav.addStretch()
        nav.addWidget(self.btn_avancar)
        root.addLayout(nav)

        self._atualizar_nav()

    # ------------------------------------------------------------------ passo 1
    def _passo1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<b>Passo 1 — Nome e formato</b>"))

        layout.addWidget(QLabel("Nome do torneio:"))
        self.input_nome = QLineEdit()
        layout.addWidget(self.input_nome)

        layout.addWidget(QLabel("Formato:"))
        self.combo_formato = QComboBox()
        for f in FORMATOS:
            self.combo_formato.addItem(f"{f} times", f)
        self.combo_formato.setCurrentIndex(1)  # 32 padrão
        layout.addWidget(self.combo_formato)

        layout.addStretch()
        return w

    # ------------------------------------------------------------------ passo 2
    def _passo2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<b>Passo 2 — Escolher times</b>"))

        topo = QHBoxLayout()
        self.label_contagem = QLabel("")
        topo.addWidget(self.label_contagem)
        topo.addStretch()
        btn_auto = QPushButton("Preencher automaticamente")
        btn_auto.clicked.connect(self._autoselecionar_times)
        topo.addWidget(btn_auto)
        layout.addLayout(topo)

        self.lista_times = QListWidget()
        self.lista_times.setSelectionMode(QListWidget.MultiSelection)
        for tid, nome in sorted(TEAM_IDS.items(), key=lambda x: x[1]):
            item = QListWidgetItem(nome)
            item.setData(Qt.UserRole, tid)
            self.lista_times.addItem(item)
        self.lista_times.itemSelectionChanged.connect(self._atualizar_contagem)
        layout.addWidget(self.lista_times)

        return w

    def _autoselecionar_times(self):
        fmt = self.combo_formato.currentData()
        todos = list(range(self.lista_times.count()))
        selecionados = random.sample(todos, min(fmt, len(todos)))
        self.lista_times.clearSelection()
        for i in selecionados:
            self.lista_times.item(i).setSelected(True)

    def _atualizar_contagem(self):
        fmt = self.combo_formato.currentData()
        n = len(self.lista_times.selectedItems())
        self.label_contagem.setText(f"{n} / {fmt} selecionados")

    # ------------------------------------------------------------------ passo 3
    def _passo3(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<b>Passo 3 — Jogadores</b>"))
        layout.addWidget(QLabel("Informe o nome do jogador para cada time. Pode deixar em branco."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.layout_jogadores = QVBoxLayout(inner)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_auto = QPushButton("Preencher automaticamente (Jogador 1, 2...)")
        btn_auto.clicked.connect(self._autopreencher_jogadores)
        layout.addWidget(btn_auto)

        self._jogador_inputs: list[tuple[Time, QLineEdit]] = []
        return w

    def _autopreencher_jogadores(self):
        for i, (time, inp) in enumerate(self._jogador_inputs):
            inp.setText(f"Jogador {i + 1}")

    def _popular_passo3(self):
        while self.layout_jogadores.count():
            item = self.layout_jogadores.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._jogador_inputs.clear()

        for time in self.times_selecionados:
            row = QHBoxLayout()
            lbl = QLabel(time.nome_time)
            lbl.setMinimumWidth(180)
            inp = QLineEdit()
            inp.setMaxLength(13)  # <---
            inp.setPlaceholderText("Nome do jogador (opcional)")
            inp.setText(time.nome_jogador)
            row.addWidget(lbl)
            row.addWidget(inp)
            container = QWidget()
            container.setLayout(row)
            self.layout_jogadores.addWidget(container)
            self._jogador_inputs.append((time, inp))

    # ------------------------------------------------------------------ passo 4
    def _passo4(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<b>Passo 4 — Sorteio</b>"))

        self.label_sorteio = QLabel("Clique em Sortear para gerar os grupos / chaveamento.")
        self.label_sorteio.setWordWrap(True)
        layout.addWidget(self.label_sorteio)

        self.area_sorteio = QScrollArea()
        self.area_sorteio.setWidgetResizable(True)
        self.widget_sorteio = QLabel("—")
        self.widget_sorteio.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.widget_sorteio.setWordWrap(True)
        self.area_sorteio.setWidget(self.widget_sorteio)
        layout.addWidget(self.area_sorteio)

        btn_sortear = QPushButton("Sortear novamente")
        btn_sortear.clicked.connect(self._sortear)
        layout.addWidget(btn_sortear)

        return w

    def _sortear(self):
        torneio_mock = Torneio(id=0, nome="", formato=self.formato)
        if self.formato == Formato.F16:
            self.jogos_matamata = engine.sortear_chaveamento_16(self.times_selecionados, 0)
            self.grupos = []
            linhas = ["<b>Chaveamento:</b><br>"]
            for j in self.jogos_matamata:
                linhas.append(f"{j.time1.nome_time} vs {j.time2.nome_time}")
            self.widget_sorteio.setText("<br>".join(linhas))
        else:
            torneio_mock.grupos = []
            self.grupos = engine.sortear_grupos(torneio_mock, self.times_selecionados)
            linhas = []
            for g in self.grupos:
                linhas.append(f"<b>Grupo {g.nome}:</b>")
                for t in g.times:
                    jog = f" ({t.nome_jogador})" if t.nome_jogador else ""
                    linhas.append(f"  • {t.nome_time}{jog}")
                linhas.append("")
            self.widget_sorteio.setText("<br>".join(linhas))

    # ------------------------------------------------------------------ navegação
    def _atualizar_nav(self):
        idx = self.stack.currentIndex()
        self.btn_voltar.setEnabled(idx > 0)
        if idx == 3:
            self.btn_avancar.setText("Confirmar")
        else:
            self.btn_avancar.setText("Avançar")

    def _voltar(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self._atualizar_nav()

    def _avancar(self):
        idx = self.stack.currentIndex()

        if idx == 0:
            nome = self.input_nome.text().strip()
            if not nome:
                QMessageBox.warning(self, "Aviso", "Informe o nome do torneio.")
                return
            self.nome = nome
            self.formato = Formato(self.combo_formato.currentData())
            self._atualizar_contagem()

        elif idx == 1:
            fmt = self.formato.value
            selecionados = self.lista_times.selectedItems()
            if len(selecionados) != fmt:
                QMessageBox.warning(self, "Aviso", f"Selecione exatamente {fmt} times.")
                return
            self.times_selecionados = [
                Time(id_time=item.data(Qt.UserRole), nome_time=item.text(), nome_jogador="")
                for item in selecionados
            ]
            self._popular_passo3()

        elif idx == 2:
            # salva nomes dos jogadores
            for time, inp in self._jogador_inputs:
                time.nome_jogador = inp.text().strip()
            # sorteia automaticamente ao entrar no passo 4
            self._sortear()

        elif idx == 3:
            if not self.grupos and not self.jogos_matamata:
                QMessageBox.warning(self, "Aviso", "Faça o sorteio antes de confirmar.")
                return
            self.accept()
            return

        self.stack.setCurrentIndex(idx + 1)
        self._atualizar_nav()
