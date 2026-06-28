import random
from typing import Optional
from app.models import (
    Torneio, Grupo, Time, Jogo, Classificacao,
    Formato, StatusJogo
)

LETRAS = "ABCDEFGHIJKLMNOP"


# ------------------------------------------------------------------ Grupos
def sortear_grupos(torneio: Torneio, times: list[Time]) -> list[Grupo]:
    shuffled = times[:]
    random.shuffle(shuffled)

    fmt = torneio.formato.value
    if fmt == 32:
        n_grupos, por_grupo = 8, 4
    else:
        return []

    grupos = []
    for i in range(n_grupos):
        g = Grupo(id=None, id_torneio=torneio.id or 0, nome=LETRAS[i])
        g.times = shuffled[i * por_grupo: (i + 1) * por_grupo]
        grupos.append(g)
    return grupos


def gerar_jogos_grupo(grupo: Grupo, id_torneio: int) -> list[Jogo]:
    times = grupo.times
    jogos = []
    n = len(times)
    pares = [(i, j) for i in range(n) for j in range(i + 1, n)]
    for idx, (a, b) in enumerate(pares):
        rodada = [1, 1, 2, 2, 3, 3][idx] if n == 4 and idx < 6 else idx + 1
        j = Jogo(
            id=None,
            id_torneio=id_torneio,
            fase="grupos",
            id_grupo=grupo.id,
            rodada=rodada,
            time1=times[a],
            time2=times[b],
        )
        jogos.append(j)
    return jogos


def _aplicar_resultado(cls: dict, j: Jogo, gols1: int, gols2: int):
    c1 = cls[j.time1.id_time]
    c2 = cls[j.time2.id_time]
    c1.gols_pro += gols1
    c1.gols_contra += gols2
    c2.gols_pro += gols2
    c2.gols_contra += gols1
    if gols1 > gols2:
        c1.vitorias += 1
        c1.pontos += 3
        c2.derrotas += 1
    elif gols2 > gols1:
        c2.vitorias += 1
        c2.pontos += 3
        c1.derrotas += 1
    else:
        c1.empates += 1
        c2.empates += 1
        c1.pontos += 1
        c2.pontos += 1


def recalcular_classificacao(
    grupo: Grupo,
    jogo_parcial: Optional[Jogo] = None,
) -> list[Classificacao]:
    """
    Recalcula a classificação do grupo.
    jogo_parcial: se passado, inclui o placar atual desse jogo
    mesmo sem estar encerrado (exibição em tempo real).
    """
    cls: dict[int, Classificacao] = {}
    for t in grupo.times:
        cls[t.id_time] = Classificacao(time=t)

    for j in grupo.jogos:
        if j.status == StatusJogo.ENCERRADO and j.gols1 is not None:
            _aplicar_resultado(cls, j, j.gols1, j.gols2)
        elif (
            jogo_parcial is not None
            and j.id == jogo_parcial.id
            and jogo_parcial.gols1 is not None
        ):
            _aplicar_resultado(cls, j, jogo_parcial.gols1, jogo_parcial.gols2)

    resultado = list(cls.values())
    resultado.sort(
        key=lambda c: (
            c.pontos,   # 1. Pontos
            c.saldo,    # 2. Saldo de gols
            c.gols_pro, # 3. Gols pró
        ),
        reverse=True,
    )
    grupo.classificacao = resultado
    return resultado





# ------------------------------------------------------------------ Chaveamento
def sortear_chaveamento_16(times: list[Time], id_torneio: int) -> list[Jogo]:
    shuffled = times[:]
    random.shuffle(shuffled)
    jogos = []
    for i in range(0, 16, 2):
        j = Jogo(
            id=None,
            id_torneio=id_torneio,
            fase="oitavas",
            id_grupo=None,
            rodada=1,
            time1=shuffled[i],
            time2=shuffled[i + 1],
        )
        jogos.append(j)
    return jogos


def gerar_chaveamento_pos_grupos(torneio: Torneio) -> list[Jogo]:
    """
    Gera os jogos da primeira fase do mata-mata após os grupos.
    F32: 8 grupos → 16 classificados (1º e 2º de cada) → oitavas
         cruzamento: 1ºA×2ºB, 1ºB×2ºA, 1ºC×2ºD, 1ºD×2ºC, ...
    F16: fase de grupos não existe (mata-mata direto), não chama esta função.
    """
    fmt = torneio.formato
    grupos = torneio.grupos

    if fmt == Formato.F32:
        classificados = []  # lista de pares (time1, time2)
        for i in range(0, len(grupos), 2):
            g1 = grupos[i]
            g2 = grupos[i + 1] if i + 1 < len(grupos) else grupos[i]
            if len(g1.classificacao) >= 2 and len(g2.classificacao) >= 2:
                # 1º do grupo A enfrenta 2º do grupo B e vice-versa
                classificados.append((g1.classificacao[0].time, g2.classificacao[1].time))
                classificados.append((g2.classificacao[0].time, g1.classificacao[1].time))
    else:
        return []

    # F32 tem 8 grupos → 8 pares → oitavas (16 times)
    fase = "oitavas" if len(classificados) >= 8 else "quartas"
    jogos = []
    for t1, t2 in classificados:
        j = Jogo(
            id=None,
            id_torneio=torneio.id or 0,
            fase=fase,
            id_grupo=None,
            rodada=1,
            time1=t1,
            time2=t2,
        )
        jogos.append(j)
    return jogos


def avancar_mata_mata(torneio: Torneio) -> list[Jogo]:
    """
    Verifica se a fase de mata-mata mais recente foi concluída e, se sim,
    gera os jogos da próxima fase.

    Lógica corrigida: encontra a fase mais avançada que já está encerrada
    E ainda não tem a próxima fase gerada — evita duplicar jogos.
    """
    fases = ["oitavas", "quartas", "semi", "final"]

    # Descobre quais fases já existem no torneio (encerradas ou não)
    fases_existentes = {j.fase for j in torneio.jogos_matamata}

    for fase in fases:
        js = [j for j in torneio.jogos_matamata if j.fase == fase]
        if not js:
            continue  # esta fase ainda não começou — nada a avançar aqui

        todos_encerrados = all(j.status == StatusJogo.ENCERRADO for j in js)
        if not todos_encerrados:
            return []  # fase em andamento, aguarda terminar

        # Fase encerrada — verifica se a próxima já foi gerada
        idx = fases.index(fase)
        if idx + 1 >= len(fases):
            return []  # era a final, torneio encerrado

        proxima = fases[idx + 1]
        if proxima in fases_existentes:
            # próxima fase já existe, continua o loop para verificar ela
            continue

        # Próxima fase ainda não existe → gera agora
        vencedores = []
        for j in js:
            if j.vencedor_id == j.time1.id_time:
                vencedores.append(j.time1)
            elif j.vencedor_id == j.time2.id_time:
                vencedores.append(j.time2)
            else:
                # empate sem vencedor definido (não deveria ocorrer, mas por segurança)
                vencedores.append(j.time1)

        novos = []
        for i in range(0, len(vencedores), 2):
            if i + 1 < len(vencedores):
                novo = Jogo(
                    id=None,
                    id_torneio=torneio.id or 0,
                    fase=proxima,
                    id_grupo=None,
                    rodada=1,
                    time1=vencedores[i],
                    time2=vencedores[i + 1],
                )
                novos.append(novo)
        return novos

    return []


def definir_vencedor(jogo: Jogo) -> Optional[int]:
    if jogo.gols1 is None or jogo.gols2 is None:
        return None
    if jogo.gols1 > jogo.gols2:
        return jogo.time1.id_time
    elif jogo.gols2 > jogo.gols1:
        return jogo.time2.id_time
    return None