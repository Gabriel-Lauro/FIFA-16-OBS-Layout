import sqlite3
import os
from typing import Optional
from app.models import (
    Torneio, Grupo, Time, Jogo, Classificacao,
    Formato, StatusTorneio, StatusJogo
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "torneio.db")


def _conectar() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco():
    conn = _conectar()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS torneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            formato INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'em_andamento'
        );

        CREATE TABLE IF NOT EXISTS times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_torneio INTEGER NOT NULL,
            id_time INTEGER NOT NULL,
            nome_time TEXT NOT NULL,
            nome_jogador TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (id_torneio) REFERENCES torneios(id)
        );

        CREATE TABLE IF NOT EXISTS grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_torneio INTEGER NOT NULL,
            nome TEXT NOT NULL,
            FOREIGN KEY (id_torneio) REFERENCES torneios(id)
        );

        CREATE TABLE IF NOT EXISTS grupo_times (
            id_grupo INTEGER NOT NULL,
            id_time_registro INTEGER NOT NULL,
            PRIMARY KEY (id_grupo, id_time_registro),
            FOREIGN KEY (id_grupo) REFERENCES grupos(id),
            FOREIGN KEY (id_time_registro) REFERENCES times(id)
        );

        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_torneio INTEGER NOT NULL,
            fase TEXT NOT NULL,
            id_grupo INTEGER,
            rodada INTEGER NOT NULL DEFAULT 0,
            id_time1 INTEGER NOT NULL,
            id_time2 INTEGER NOT NULL,
            gols1 INTEGER,
            gols2 INTEGER,
            status TEXT NOT NULL DEFAULT 'pendente',
            vencedor_id INTEGER,
            FOREIGN KEY (id_torneio) REFERENCES torneios(id),
            FOREIGN KEY (id_time1) REFERENCES times(id),
            FOREIGN KEY (id_time2) REFERENCES times(id)
        );

        CREATE TABLE IF NOT EXISTS classificacao (
            id_torneio INTEGER NOT NULL,
            id_grupo INTEGER NOT NULL,
            id_time_registro INTEGER NOT NULL,
            pontos INTEGER NOT NULL DEFAULT 0,
            vitorias INTEGER NOT NULL DEFAULT 0,
            empates INTEGER NOT NULL DEFAULT 0,
            derrotas INTEGER NOT NULL DEFAULT 0,
            gols_pro INTEGER NOT NULL DEFAULT 0,
            gols_contra INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (id_torneio, id_grupo, id_time_registro),
            FOREIGN KEY (id_torneio) REFERENCES torneios(id),
            FOREIGN KEY (id_grupo) REFERENCES grupos(id),
            FOREIGN KEY (id_time_registro) REFERENCES times(id)
        );
    """)
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ Torneios
def salvar_torneio(torneio: Torneio) -> int:
    conn = _conectar()
    c = conn.cursor()
    c.execute(
        "INSERT INTO torneios (nome, formato, status) VALUES (?, ?, ?)",
        (torneio.nome, torneio.formato.value, torneio.status.value)
    )
    torneio_id = c.lastrowid
    conn.commit()
    conn.close()
    return torneio_id


def listar_torneios() -> list[dict]:
    conn = _conectar()
    rows = conn.execute("SELECT * FROM torneios ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def atualizar_status_torneio(id_torneio: int, status: StatusTorneio):
    conn = _conectar()
    conn.execute("UPDATE torneios SET status=? WHERE id=?", (status.value, id_torneio))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ Times
def salvar_time(id_torneio: int, time: Time) -> int:
    conn = _conectar()
    c = conn.cursor()
    c.execute(
        "INSERT INTO times (id_torneio, id_time, nome_time, nome_jogador) VALUES (?,?,?,?)",
        (id_torneio, time.id_time, time.nome_time, time.nome_jogador)
    )
    reg_id = c.lastrowid
    conn.commit()
    conn.close()
    return reg_id


def buscar_times_torneio(id_torneio: int) -> list[dict]:
    conn = _conectar()
    rows = conn.execute(
        "SELECT * FROM times WHERE id_torneio=?", (id_torneio,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def atualizar_jogador_time(id_time_registro: int, nome_jogador: str):
    conn = _conectar()
    conn.execute("UPDATE times SET nome_jogador=? WHERE id=?", (nome_jogador, id_time_registro))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ Grupos
def salvar_grupo(id_torneio: int, nome: str, ids_times_registro: list[int]) -> int:
    conn = _conectar()
    c = conn.cursor()
    c.execute("INSERT INTO grupos (id_torneio, nome) VALUES (?,?)", (id_torneio, nome))
    grupo_id = c.lastrowid
    for tid in ids_times_registro:
        c.execute("INSERT INTO grupo_times (id_grupo, id_time_registro) VALUES (?,?)", (grupo_id, tid))
    conn.commit()
    conn.close()
    return grupo_id


def buscar_grupos_torneio(id_torneio: int) -> list[dict]:
    conn = _conectar()
    rows = conn.execute("SELECT * FROM grupos WHERE id_torneio=? ORDER BY nome", (id_torneio,)).fetchall()
    grupos = []
    for row in rows:
        g = dict(row)
        times_rows = conn.execute("""
            SELECT t.* FROM times t
            JOIN grupo_times gt ON gt.id_time_registro = t.id
            WHERE gt.id_grupo=?
        """, (row["id"],)).fetchall()
        g["times"] = [dict(t) for t in times_rows]
        grupos.append(g)
    conn.close()
    return grupos


# ------------------------------------------------------------------ Jogos
def salvar_jogo(id_torneio: int, jogo: Jogo, id_time1_reg: int, id_time2_reg: int, id_grupo: Optional[int] = None) -> int:
    conn = _conectar()
    c = conn.cursor()
    c.execute("""
        INSERT INTO jogos (id_torneio, fase, id_grupo, rodada, id_time1, id_time2, gols1, gols2, status, vencedor_id)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        id_torneio, jogo.fase, id_grupo, jogo.rodada,
        id_time1_reg, id_time2_reg,
        jogo.gols1, jogo.gols2,
        jogo.status.value, jogo.vencedor_id
    ))
    jogo_id = c.lastrowid
    conn.commit()
    conn.close()
    return jogo_id


def atualizar_jogo(jogo_id: int, gols1: int, gols2: int, status: StatusJogo, vencedor_id: Optional[int]):
    conn = _conectar()
    conn.execute(
        "UPDATE jogos SET gols1=?, gols2=?, status=?, vencedor_id=? WHERE id=?",
        (gols1, gols2, status.value, vencedor_id, jogo_id)
    )
    conn.commit()
    conn.close()


def cancelar_jogo(jogo_id: int):
    conn = _conectar()
    conn.execute(
        "UPDATE jogos SET status='pendente', gols1=NULL, gols2=NULL, vencedor_id=NULL WHERE id=?",
        (jogo_id,)
    )
    conn.commit()
    conn.close()


def buscar_jogos_torneio(id_torneio: int) -> list[dict]:
    conn = _conectar()
    rows = conn.execute(
        "SELECT * FROM jogos WHERE id_torneio=? ORDER BY fase, rodada, id",
        (id_torneio,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ Classificação
def inicializar_classificacao(id_torneio: int, id_grupo: int, id_time_registro: int):
    conn = _conectar()
    conn.execute("""
        INSERT OR IGNORE INTO classificacao
        (id_torneio, id_grupo, id_time_registro, pontos, vitorias, empates, derrotas, gols_pro, gols_contra)
        VALUES (?,?,?,0,0,0,0,0,0)
    """, (id_torneio, id_grupo, id_time_registro))
    conn.commit()
    conn.close()


def atualizar_classificacao(id_torneio: int, id_grupo: int, id_time_registro: int, c: Classificacao):
    conn = _conectar()
    conn.execute("""
        UPDATE classificacao SET pontos=?, vitorias=?, empates=?, derrotas=?, gols_pro=?, gols_contra=?
        WHERE id_torneio=? AND id_grupo=? AND id_time_registro=?
    """, (
        c.pontos, c.vitorias, c.empates, c.derrotas, c.gols_pro, c.gols_contra,
        id_torneio, id_grupo, id_time_registro
    ))
    conn.commit()
    conn.close()


def buscar_classificacao_grupo(id_torneio: int, id_grupo: int) -> list[dict]:
    conn = _conectar()
    rows = conn.execute(
        "SELECT * FROM classificacao WHERE id_torneio=? AND id_grupo=? ORDER BY pontos DESC",
        (id_torneio, id_grupo)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ Carregar torneio completo
def carregar_torneio_completo(id_torneio: int) -> Optional[Torneio]:
    conn = _conectar()
    row = conn.execute("SELECT * FROM torneios WHERE id=?", (id_torneio,)).fetchone()
    if not row:
        conn.close()
        return None
    conn.close()

    torneio = Torneio(
        id=row["id"],
        nome=row["nome"],
        formato=Formato(row["formato"]),
        status=StatusTorneio(row["status"]),
    )

    times_rows = buscar_times_torneio(id_torneio)
    times_map = {}
    for t in times_rows:
        obj = Time(id_time=t["id_time"], nome_time=t["nome_time"], nome_jogador=t["nome_jogador"])
        times_map[t["id"]] = obj

    grupos_rows = buscar_grupos_torneio(id_torneio)
    for gr in grupos_rows:
        grupo = Grupo(id=gr["id"], id_torneio=id_torneio, nome=gr["nome"])
        for tr in gr["times"]:
            if tr["id"] in times_map:
                grupo.times.append(times_map[tr["id"]])
        torneio.grupos.append(grupo)

    conn2 = _conectar()
    jogos_rows = conn2.execute(
        "SELECT * FROM jogos WHERE id_torneio=? ORDER BY rodada, id",
        (id_torneio,)
    ).fetchall()
    conn2.close()

    grupos_por_id = {g.id: g for g in torneio.grupos}

    for jr in jogos_rows:
        if jr["id_time1"] not in times_map or jr["id_time2"] not in times_map:
            continue
        j = Jogo(
            id=jr["id"],
            id_torneio=id_torneio,
            fase=jr["fase"],
            id_grupo=jr["id_grupo"],
            rodada=jr["rodada"],
            time1=times_map[jr["id_time1"]],
            time2=times_map[jr["id_time2"]],
            gols1=jr["gols1"],
            gols2=jr["gols2"],
            status=StatusJogo(jr["status"]),
            vencedor_id=jr["vencedor_id"],
        )
        if jr["fase"] == "grupos" and jr["id_grupo"] and jr["id_grupo"] in grupos_por_id:
            grupos_por_id[jr["id_grupo"]].jogos.append(j)
        else:
            torneio.jogos_matamata.append(j)

    # classificação — recalcula sempre a partir dos jogos em memória
    # (o banco pode estar desatualizado se o app fechou com jogo em andamento)
    from app.engine import recalcular_classificacao
    for grupo in torneio.grupos:
        recalcular_classificacao(grupo)

    return torneio
