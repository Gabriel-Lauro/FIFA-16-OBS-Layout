import threading
from typing import Optional, Callable
from app.models import Torneio, Jogo, StatusJogo


class EstadoTorneio:
    def __init__(self):
        self._lock = threading.Lock()
        self._torneio: Optional[Torneio] = None
        self._jogo_atual: Optional[Jogo] = None
        self._gols1: int = 0
        self._gols2: int = 0
        self._fifa_conectado: bool = False
        self._leitura_ativa: bool = False
        self._callbacks_placar: list[Callable] = []
        self._callbacks_conexao: list[Callable] = []

    # ------------------------------------------------------------------ torneio
    def set_torneio(self, torneio: Torneio):
        with self._lock:
            self._torneio = torneio

    def get_torneio(self) -> Optional[Torneio]:
        with self._lock:
            return self._torneio

    # ------------------------------------------------------------------ jogo
    def iniciar_jogo(self, jogo: Jogo):
        with self._lock:
            self._jogo_atual = jogo
            self._gols1 = 0
            self._gols2 = 0
            jogo.status = StatusJogo.EM_ANDAMENTO
            jogo.gols1 = 0
            jogo.gols2 = 0

    def encerrar_jogo(self):
        with self._lock:
            if self._jogo_atual:
                self._jogo_atual.status = StatusJogo.ENCERRADO
                self._jogo_atual.gols1 = self._gols1
                self._jogo_atual.gols2 = self._gols2
            self._leitura_ativa = False
            j = self._jogo_atual
            self._jogo_atual = None
            return j

    def get_jogo_atual(self) -> Optional[Jogo]:
        with self._lock:
            return self._jogo_atual

    def interromper_jogo(self):
        with self._lock:
            if self._jogo_atual:
                self._jogo_atual.status = StatusJogo.PENDENTE
                self._jogo_atual.gols1 = None
                self._jogo_atual.gols2 = None
            self._leitura_ativa = False
            self._jogo_atual = None

    # ------------------------------------------------------------------ placar
    def _recalcular_parcial(self):
        """
        Recalcula a classificação do grupo do jogo em andamento
        incluindo o placar parcial atual. Chamado sem o lock.
        Só considera o placar parcial se ao menos um gol foi marcado,
        evitando que o 0x0 inicial afete a classificação.
        """
        from app import engine
        with self._lock:
            j = self._jogo_atual
            t = self._torneio
            g1 = self._gols1
            g2 = self._gols2
        if not j or not t or j.fase != "grupos":
            return
        jogo_parcial = j if (g1 > 0 or g2 > 0) else None
        for grupo in t.grupos:
            if grupo.id == j.id_grupo:
                engine.recalcular_classificacao(grupo, jogo_parcial=jogo_parcial)
                break

    def atualizar_placar(self, gols1: int, gols2: int):
        """Atualiza diretamente (gols1 = time1 do jogo, gols2 = time2)."""
        changed = False
        with self._lock:
            if gols1 != self._gols1 or gols2 != self._gols2:
                self._gols1 = gols1
                self._gols2 = gols2
                if self._jogo_atual:
                    self._jogo_atual.gols1 = gols1
                    self._jogo_atual.gols2 = gols2
                changed = True
        if changed:
            self._recalcular_parcial()
            for cb in self._callbacks_placar:
                cb(self._gols1, self._gols2)

    def atualizar_placar_por_id(
        self,
        home_team_id: int, home_goals: int,
        away_team_id: int, away_goals: int,
    ):
        """
        Recebe os IDs e gols lidos da memória (casa/visitante do FIFA)
        e os mapeia para time1/time2 do jogo cadastrado no sistema.
        """
        g1 = g2 = None
        with self._lock:
            j = self._jogo_atual
            if not j:
                return

            id1 = j.time1.id_time
            id2 = j.time2.id_time

            if home_team_id == id1 and away_team_id == id2:
                g1, g2 = home_goals, away_goals
            elif home_team_id == id2 and away_team_id == id1:
                g1, g2 = away_goals, home_goals
            else:
                return

            if g1 == self._gols1 and g2 == self._gols2:
                return

            self._gols1 = g1
            self._gols2 = g2
            j.gols1 = g1
            j.gols2 = g2

        self._recalcular_parcial()
        for cb in self._callbacks_placar:
            cb(g1, g2)

    def get_placar(self) -> tuple[int, int]:
        with self._lock:
            return self._gols1, self._gols2

    # ------------------------------------------------------------------ conexão
    def set_fifa_conectado(self, conectado: bool):
        with self._lock:
            prev = self._fifa_conectado
            self._fifa_conectado = conectado
        if conectado != prev:
            for cb in self._callbacks_conexao:
                cb(conectado)

    def get_fifa_conectado(self) -> bool:
        with self._lock:
            return self._fifa_conectado

    # ------------------------------------------------------------------ leitura
    def set_leitura_ativa(self, ativa: bool):
        with self._lock:
            self._leitura_ativa = ativa

    def get_leitura_ativa(self) -> bool:
        with self._lock:
            return self._leitura_ativa

    # ------------------------------------------------------------------ callbacks
    def on_placar(self, cb: Callable):
        self._callbacks_placar.append(cb)

    def on_conexao(self, cb: Callable):
        self._callbacks_conexao.append(cb)

    # ------------------------------------------------------------------ snapshots SSE
    def snapshot_aovivo(self) -> dict:
        with self._lock:
            j = self._jogo_atual
            if not j:
                return {"jogo": None, "grupo": None}

            grupo_snapshot = None
            partidas_snapshot = None

            if j.fase == "grupos" and self._torneio:
                for g in self._torneio.grupos:
                    if g.id == j.id_grupo:
                        grupo_snapshot = _serializar_grupo(g, j)
                        break

            elif self._torneio:
                fase_atual = j.fase
                partidas_snapshot = [
                    {
                        "t1": jm.time1.nome_time,
                        "t2": jm.time2.nome_time,
                        "s1": jm.gols1,
                        "s2": jm.gols2,
                        "status": jm.status.value,
                    }
                    for jm in self._torneio.jogos_matamata
                    if jm.fase == fase_atual
                ]

            return {
                "jogo": {
                    "fase": j.fase,
                    "id_grupo": j.id_grupo,
                    "time1": j.time1.nome_time,
                    "jogador1": j.time1.nome_jogador,
                    "time2": j.time2.nome_time,
                    "jogador2": j.time2.nome_jogador,
                    "gols1": self._gols1,
                    "gols2": self._gols2,
                    "status": j.status.value,
                    "fifa_conectado": self._fifa_conectado,
                },
                "grupo": grupo_snapshot,
                "partidas": partidas_snapshot,
                "fase": j.fase if partidas_snapshot is not None else None,
            }

    def snapshot_grupos(self) -> dict:
        with self._lock:
            t = self._torneio
            if not t:
                return {"torneio": None}

            j_atual = self._jogo_atual

            grupos = [
                _serializar_grupo(g, j_atual)
                for g in t.grupos
            ]
            matamata = [
                {
                    "fase": j.fase,
                    "time1": j.time1.nome_time,
                    "time2": j.time2.nome_time,
                    "gols1": j.gols1,
                    "gols2": j.gols2,
                    "status": j.status.value,
                }
                for j in t.jogos_matamata
            ]
            return {
                "torneio": {
                    "nome": t.nome,
                    "formato": t.formato.value,
                    "fase_atual": "grupos" if grupos else "matamata",
                    "grupos": grupos,
                    "matamata": matamata,
                }
            }


def _serializar_grupo(g, j_atual=None) -> dict:
    """Serializa um grupo. j_atual marca os times em campo."""
    ids_em_jogo = set()
    if j_atual and j_atual.id_grupo == g.id:
        ids_em_jogo = {j_atual.time1.id_time, j_atual.time2.id_time}

    return {
        "nome": g.nome,
        "classificacao": [
            {
                "time": c.time.nome_time,
                "jogador": c.time.nome_jogador,
                "pontos": c.pontos,
                "v": c.vitorias,
                "e": c.empates,
                "d": c.derrotas,
                "gp": c.gols_pro,
                "gc": c.gols_contra,
                "sg": c.saldo,
                "em_jogo": c.time.id_time in ids_em_jogo,
            }
            for c in sorted(
                g.classificacao,
                key=lambda x: (x.pontos, x.saldo, x.gols_pro),
                reverse=True,
            )
        ],
    }


estado = EstadoTorneio()