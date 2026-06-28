import sys
import os
import webbrowser

from PySide6.QtWidgets import QApplication, QMenuBar, QMenu, QMessageBox, QDialog
from PySide6.QtGui import QAction

# garante que imports de 'app.' funcionem
sys.path.insert(0, os.path.dirname(__file__))

import app.database as db
from app.state import estado
from app.models import Torneio, Grupo, Jogo, StatusJogo, Formato
from app import engine, server
from app.memory import MemoryReader
from app.times import TEAM_IDS

from app.ui.dialogo_inicio import DialogoInicio
from app.ui.wizard import WizardNovoTorneio
from app.ui.main_window import MainWindow
from app.ui.admin_window import AdminWindow
from app.ui.configuracoes import DialogoConfiguracoes


_memory_reader: MemoryReader | None = None
_main_window: MainWindow | None = None
_browser_aberto = False
_torneio_id: int | None = None

# mapa: id_time_registro -> Time (para reconstruir refs após salvar)
_times_reg_map: dict[int, object] = {}


def main():
    global _main_window

    db.inicializar_banco()
    server.iniciar_servidor(estado)

    app = QApplication(sys.argv)

    dialogo = DialogoInicio()
    if dialogo.exec() != QDialog.Accepted:
        sys.exit(0)

    if dialogo.acao == "novo":
        _criar_novo_torneio(app)
    else:
        _carregar_torneio(dialogo.torneio_id_selecionado, app)

    sys.exit(app.exec())


def _criar_novo_torneio(app):
    global _torneio_id, _times_reg_map

    wiz = WizardNovoTorneio()
    if wiz.exec() != QDialog.Accepted:
        sys.exit(0)

    torneio = Torneio(id=None, nome=wiz.nome, formato=wiz.formato)
    tid = db.salvar_torneio(torneio)
    torneio.id = tid
    _torneio_id = tid
    estado.set_torneio(torneio)

    # salva times
    _times_reg_map = {}
    for time in wiz.times_selecionados:
        reg_id = db.salvar_time(tid, time)
        _times_reg_map[reg_id] = time

    # salva grupos / jogos
    if wiz.formato == Formato.F16:
        for j in wiz.jogos_matamata:
            t1_reg = _reg_id_for(j.time1)
            t2_reg = _reg_id_for(j.time2)
            jid = db.salvar_jogo(tid, j, t1_reg, t2_reg)
            j.id = jid
        torneio.jogos_matamata = wiz.jogos_matamata
    else:
        for g in wiz.grupos:
            ids_times_reg = [_reg_id_for(t) for t in g.times]
            gid = db.salvar_grupo(tid, g.nome, ids_times_reg)
            g.id = gid
            g.id_torneio = tid

            # inicializa classificação
            for reg_id in ids_times_reg:
                db.inicializar_classificacao(tid, gid, reg_id)

            # gera e salva jogos do grupo
            jogos = engine.gerar_jogos_grupo(g, tid)
            for j in jogos:
                j.id_grupo = gid
                t1_reg = _reg_id_for(j.time1)
                t2_reg = _reg_id_for(j.time2)
                jid = db.salvar_jogo(tid, j, t1_reg, t2_reg, gid)
                j.id = jid
            g.jogos = jogos
            g.classificacao = engine.recalcular_classificacao(g)

        torneio.grupos = wiz.grupos

    _abrir_main_window(app, torneio)


def _reg_id_for(time) -> int:
    """Retorna o id de registro (tabela times) para um Time."""
    for reg_id, t in _times_reg_map.items():
        if t.id_time == time.id_time:
            return reg_id
    raise ValueError(f"Time não encontrado no mapa: {time.id_time}")


def _carregar_torneio(torneio_id: int, app):
    global _torneio_id, _times_reg_map

    torneio = db.carregar_torneio_completo(torneio_id)
    if not torneio:
        QMessageBox.critical(None, "Erro", "Não foi possível carregar o torneio.")
        sys.exit(1)

    _torneio_id = torneio_id
    estado.set_torneio(torneio)

    # reconstrói mapa
    times_rows = db.buscar_times_torneio(torneio_id)
    _times_reg_map = {
        row["id"]: next(
            (t for g in torneio.grupos for t in g.times if t.id_time == row["id_time"]),
            None
        ) or next(
            (j.time1 for j in torneio.jogos_matamata if j.time1.id_time == row["id_time"]),
            None
        )
        for row in times_rows
    }

    _abrir_main_window(app, torneio)


def _abrir_main_window(app, torneio: Torneio):
    global _main_window

    _main_window = MainWindow(
        torneio=torneio,
        estado=estado,
        on_iniciar_jogo=_iniciar_jogo,
        on_interromper=_interromper_jogo,
        on_editar_jogo=_editar_jogo,
    )

    # menu configurações
    menu_bar = _main_window.menuBar()
    menu_cfg = menu_bar.addMenu("Opções")
    action_cfg = QAction("Configurações de memória", _main_window)
    action_cfg.triggered.connect(_abrir_configuracoes)
    menu_cfg.addAction(action_cfg)

    _main_window.show()


def _iniciar_jogo(jogo: Jogo):
    global _memory_reader, _browser_aberto

    # se já há jogo em andamento e é o mesmo, abre admin
    jogo_atual = estado.get_jogo_atual()
    if jogo_atual and jogo_atual.id == jogo.id:
        _abrir_admin(jogo)
        return

    # marca em andamento no banco
    db.atualizar_jogo(jogo.id, 0, 0, StatusJogo.EM_ANDAMENTO, None)
    estado.iniciar_jogo(jogo)

    # broadcast imediato: browser já vê o jogo novo com 0x0
    # antes de qualquer leitura de memória chegar
    server.broadcast_aovivo()
    server.broadcast_grupos()

    # inicia reader de memória
    if _memory_reader:
        _memory_reader.parar()
    _memory_reader = MemoryReader(estado)
    _memory_reader.iniciar()

    # abre browser na primeira partida
    if not _browser_aberto:
        webbrowser.open("http://localhost:8000/grupos")
        webbrowser.open("http://localhost:8000/aovivo")
        _browser_aberto = True

    _abrir_admin(jogo)


def _abrir_admin(jogo: Jogo):
    admin = AdminWindow(jogo, estado, _main_window)
    resultado = admin.exec()

    if resultado == QDialog.Accepted:
        _encerrar_jogo(jogo)


def _encerrar_jogo(jogo: Jogo):
    global _memory_reader

    if _memory_reader:
        _memory_reader.parar()
        _memory_reader = None

    jogo_encerrado = estado.encerrar_jogo()
    if not jogo_encerrado:
        return

    g1, g2 = jogo_encerrado.gols1 or 0, jogo_encerrado.gols2 or 0
    vencedor_id = engine.definir_vencedor(jogo_encerrado)
    jogo_encerrado.vencedor_id = vencedor_id

    db.atualizar_jogo(jogo_encerrado.id, g1, g2, StatusJogo.ENCERRADO, vencedor_id)

    torneio = estado.get_torneio()

    # recalcula classificação se for jogo de grupo
    if jogo_encerrado.fase == "grupos":
        for grupo in torneio.grupos:
            if grupo.id == jogo_encerrado.id_grupo:
                engine.recalcular_classificacao(grupo)
                for c in grupo.classificacao:
                    reg_id = _reg_id_for(c.time)
                    db.atualizar_classificacao(torneio.id, grupo.id, reg_id, c)

        # verifica se fase de grupos terminou
        todos_jogos_grupos = [j for g in torneio.grupos for j in g.jogos]
        if all(j.status == StatusJogo.ENCERRADO for j in todos_jogos_grupos):
            _gerar_matamata(torneio)

    else:
        # verifica se fase de mata-mata atual terminou e avança
        novos = engine.avancar_mata_mata(torneio)
        if novos:
            for j in novos:
                t1_reg = _reg_id_for(j.time1)
                t2_reg = _reg_id_for(j.time2)
                jid = db.salvar_jogo(torneio.id, j, t1_reg, t2_reg)
                j.id = jid
            torneio.jogos_matamata.extend(novos)

    server.broadcast_grupos()
    if _main_window:
        _main_window.atualizar()


def _gerar_matamata(torneio: Torneio):
    jogos = engine.gerar_chaveamento_pos_grupos(torneio)
    for j in jogos:
        t1_reg = _reg_id_for(j.time1)
        t2_reg = _reg_id_for(j.time2)
        jid = db.salvar_jogo(torneio.id, j, t1_reg, t2_reg)
        j.id = jid
    torneio.jogos_matamata.extend(jogos)


def _interromper_jogo():
    global _memory_reader

    jogo_atual = estado.get_jogo_atual()
    if not jogo_atual:
        return

    if _memory_reader:
        _memory_reader.parar()
        _memory_reader = None

    db.cancelar_jogo(jogo_atual.id)
    estado.interromper_jogo()

    if _main_window:
        _main_window.atualizar()


def _editar_jogo(jogo: Jogo):
    """Abre um diálogo para corrigir o placar de um jogo já encerrado."""
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDialogButtonBox

    dlg = QDialog(_main_window)
    dlg.setWindowTitle(f"Editar placar — {jogo.time1.nome_time} vs {jogo.time2.nome_time}")
    dlg.setMinimumWidth(340)

    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel(f"<b>{jogo.time1.nome_time}  ×  {jogo.time2.nome_time}</b>"))

    row = QHBoxLayout()
    spin1 = QSpinBox()
    spin1.setRange(0, 20)
    spin1.setValue(jogo.gols1 or 0)
    spin2 = QSpinBox()
    spin2.setRange(0, 20)
    spin2.setValue(jogo.gols2 or 0)
    row.addWidget(QLabel(jogo.time1.nome_time))
    row.addWidget(spin1)
    row.addWidget(QLabel("×"))
    row.addWidget(spin2)
    row.addWidget(QLabel(jogo.time2.nome_time))
    layout.addLayout(row)

    btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    layout.addWidget(btns)

    if dlg.exec() != QDialog.Accepted:
        return

    g1 = spin1.value()
    g2 = spin2.value()
    jogo.gols1 = g1
    jogo.gols2 = g2
    vencedor_id = engine.definir_vencedor(jogo)
    jogo.vencedor_id = vencedor_id

    db.atualizar_jogo(jogo.id, g1, g2, StatusJogo.ENCERRADO, vencedor_id)

    torneio = estado.get_torneio()
    if jogo.fase == "grupos":
        for grupo in torneio.grupos:
            if grupo.id == jogo.id_grupo:
                engine.recalcular_classificacao(grupo)
                for c in grupo.classificacao:
                    reg_id = _reg_id_for(c.time)
                    db.atualizar_classificacao(torneio.id, grupo.id, reg_id, c)

    server.broadcast_grupos()
    if _main_window:
        _main_window.atualizar()


def _abrir_configuracoes():
    dlg = DialogoConfiguracoes(_main_window)
    dlg.exec()


if __name__ == "__main__":
    main()
