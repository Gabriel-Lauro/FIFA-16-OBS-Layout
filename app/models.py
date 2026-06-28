from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class StatusJogo(str, Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    ENCERRADO = "encerrado"


class StatusTorneio(str, Enum):
    EM_ANDAMENTO = "em_andamento"
    ENCERRADO = "encerrado"


class Formato(int, Enum):
    F16 = 16
    F32 = 32


@dataclass
class Time:
    id_time: int          # chave do dicionário TEAM_IDS
    nome_time: str
    nome_jogador: str     # pode ser vazio


@dataclass
class Jogo:
    id: Optional[int]
    id_torneio: int
    fase: str             # "grupos", "oitavas", "quartas", "semi", "final"
    id_grupo: Optional[int]
    rodada: int
    time1: Time
    time2: Time
    gols1: Optional[int] = None
    gols2: Optional[int] = None
    status: StatusJogo = StatusJogo.PENDENTE
    vencedor_id: Optional[int] = None


@dataclass
class Classificacao:
    time: Time
    pontos: int = 0
    vitorias: int = 0
    empates: int = 0
    derrotas: int = 0
    gols_pro: int = 0
    gols_contra: int = 0

    @property
    def saldo(self) -> int:
        return self.gols_pro - self.gols_contra


@dataclass
class Grupo:
    id: Optional[int]
    id_torneio: int
    nome: str             # "A", "B", "C"...
    times: list[Time] = field(default_factory=list)
    jogos: list[Jogo] = field(default_factory=list)
    classificacao: list[Classificacao] = field(default_factory=list)


@dataclass
class Torneio:
    id: Optional[int]
    nome: str
    formato: Formato
    status: StatusTorneio = StatusTorneio.EM_ANDAMENTO
    grupos: list[Grupo] = field(default_factory=list)
    jogos_matamata: list[Jogo] = field(default_factory=list)