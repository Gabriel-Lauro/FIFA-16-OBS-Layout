import threading
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "home_goals_offset": 0x34EB458,
    "away_goals_offset": 0x34EB45C,
    "home_team_offset":  0x34F91AC,
    "away_team_offset":  0x34F9244,
}

MAX_GOLS = 20
PROCESS_NAME = "fifa16.exe"


def carregar_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def salvar_settings(dados: dict):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(dados, f, indent=2)


def placar_valido(g1: int, g2: int) -> bool:
    return 0 <= g1 <= MAX_GOLS and 0 <= g2 <= MAX_GOLS


class MemoryReader:
    def __init__(self, estado):
        self._estado = estado
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()

    def iniciar(self):
        self._parar.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()

    def _loop(self):
        self._estado.set_leitura_ativa(True)
        pm = None
        base = None
        # só aceita gols depois que o FIFA mostrar os IDs corretos dos times
        # isso evita ler o placar residual da partida anterior
        jogo_confirmado = False

        while not self._parar.is_set():
            if pm is None:
                try:
                    import pymem
                    import pymem.process
                    pm = pymem.Pymem(PROCESS_NAME)
                    module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
                    base = module.lpBaseOfDll
                    self._estado.set_fifa_conectado(True)
                    jogo_confirmado = False
                except Exception:
                    pm = None
                    base = None
                    self._estado.set_fifa_conectado(False)
                    self._parar.wait(2)
                    continue

            try:
                cfg = carregar_settings()
                home_goals   = pm.read_int(base + cfg["home_goals_offset"])
                away_goals   = pm.read_int(base + cfg["away_goals_offset"])
                home_team_id = pm.read_int(base + cfg["home_team_offset"])
                away_team_id = pm.read_int(base + cfg["away_team_offset"])

                if not placar_valido(home_goals, away_goals):
                    self._parar.wait(1)
                    continue

                j = self._estado.get_jogo_atual()
                if j is None:
                    self._parar.wait(1)
                    continue

                id1, id2 = j.time1.id_time, j.time2.id_time
                ids_batem = (
                    (home_team_id == id1 and away_team_id == id2) or
                    (home_team_id == id2 and away_team_id == id1)
                )

                if not jogo_confirmado:
                    if ids_batem:
                        # FIFA carregou a partida correta — a partir daqui aceita gols
                        jogo_confirmado = True
                    else:
                        # ainda no menu / tela de resultado anterior — ignora
                        self._parar.wait(1)
                        continue

                self._estado.atualizar_placar_por_id(
                    home_team_id, home_goals,
                    away_team_id, away_goals,
                )

            except Exception:
                pm = None
                base = None
                self._estado.set_fifa_conectado(False)
                jogo_confirmado = False

            self._parar.wait(1)

        self._estado.set_leitura_ativa(False)
        self._estado.set_fifa_conectado(False)
