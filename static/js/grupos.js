/* ══════════════════════════════════════════════════════════════
   grupos.js — Torneio overlay
   Requisitos: ES2015+, sem dependências externas
══════════════════════════════════════════════════════════════ */

'use strict';

/* ──────────────────────────────────────────────
   CONSTANTES DO BRACKET
────────────────────────────────────────────── */

const BRACKET = Object.freeze({
  COL_W:   178,
  COL_GAP:  22,
  BOX_H:    58,
  BOX_GAP:   7,
  LBL_H:    32,
  BR_H:   1028,
  STROKE: 'rgba(140,138,104,0.5)',
  STROKE_W: 2,

  ESTRUTURA: Object.freeze({
    oitavas: 8, quartas: 4, semi: 2, final: 1,
  }),

  FASES: Object.freeze(['oitavas', 'quartas', 'semi', 'final']),

  LABELS: Object.freeze([
    [0, 'Oitavas'], [1, 'Quartas'], [2, 'Semifinal'],
    [3, 'Final'],
    [4, 'Semifinal'], [5, 'Quartas'], [6, 'Oitavas'],
  ]),
});

/**
 * Mapeamento de quantidade de grupos para modificador CSS de densidade.
 * Centraliza a lógica de layout evitando if/else espalhados.
 *
 * @type {ReadonlyArray<{ min: number, max: number, cls: string }>}
 */
const DENSIDADE_LAYOUT = Object.freeze([
  { min: 8, max: 8, cls: 'oito-grupos'    }, // 3-3-2 dedicado
  { min: 7, max: 7, cls: 'muito-compacto' }, // 4 colunas
  { min: 5, max: 6, cls: 'compacto'       }, // 3 colunas
  { min: 1, max: 4, cls: ''               }, // 2 colunas (padrão)
]);

const TOTAL_W = 7 * BRACKET.COL_W + 6 * BRACKET.COL_GAP;
const CONF_H  = BRACKET.BOX_H * 2 + BRACKET.BOX_GAP;

/* ──────────────────────────────────────────────
   UTILITÁRIOS
────────────────────────────────────────────── */

/**
 * Gera slug de URL a partir de um nome de time para uso em caminhos de imagem.
 * @param {string} nome
 * @returns {string}
 */
const slugLogo = (nome) =>
  nome.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');

/** @param {number} idx — índice da coluna (0-based) */
const colX = (idx) => idx * (BRACKET.COL_W + BRACKET.COL_GAP);

/**
 * Centro vertical de um slot dentro de uma altura total fixa.
 * @param {number} n     — total de slots na coluna
 * @param {number} idx   — índice do slot (0-based)
 */
const slotCY = (n, idx) => { const h = BRACKET.BR_H / n; return h * idx + h / 2; };

/**
 * Retorna o modificador CSS de grade conforme o número de grupos.
 * @param {number} n
 * @returns {string}
 */
function classeDensidade(n) {
  const entrada = DENSIDADE_LAYOUT.find(({ min, max }) => n >= min && n <= max);
  const cls = entrada?.cls ?? '';
  return cls ? ` ${cls}` : '';
}

/* ──────────────────────────────────────────────
   SSE
────────────────────────────────────────────── */

/** @type {EventSource|null} */
let sse = null;

/** Conecta (ou reconecta) ao endpoint SSE de torneio. */
function conectar() {
  sse?.close();
  sse = new EventSource('/stream/grupos');

  sse.onmessage = ({ data }) => {
    try {
      render(JSON.parse(data));
    } catch (err) {
      console.error('[torneio] erro ao processar mensagem SSE:', err);
    }
  };

  sse.onerror = () => {
    sse.close();
    setTimeout(conectar, 3_000);
  };
}

/* ──────────────────────────────────────────────
   RENDER PRINCIPAL
────────────────────────────────────────────── */

/**
 * Ponto de entrada do render: decide qual visão exibir.
 * @param {{ torneio?: object }} payload
 */
function render({ torneio }) {
  const root   = document.getElementById('root');
  const titulo = document.getElementById('titulo');

  if (!torneio) {
    root.innerHTML = '<div class="idle">Nenhum torneio em andamento.</div>';
    return;
  }

  titulo.textContent = torneio.nome;

  const temMatamata = torneio.matamata?.length > 0;

  if (temMatamata) {
    root.innerHTML = renderBracket(torneio.matamata);
  } else if (torneio.grupos?.length) {
    root.innerHTML = renderGrupos(torneio.grupos);
  } else {
    root.innerHTML = '<div class="idle">Aguardando dados...</div>';
  }
}

/* ══════════════════════════════════════════════════════════════
   FASE DE GRUPOS
══════════════════════════════════════════════════════════════ */

/**
 * Renderiza a seção completa de grupos.
 * @param {object[]} grupos
 * @returns {string} HTML
 */
function renderGrupos(grupos) {
  const cls   = classeDensidade(grupos.length);
  const cards = grupos.map(renderGrupoCard).join('');
  return `
    <div class="secao-titulo">Fase de Grupos</div>
    <div class="grade-grupos${cls}">${cards}</div>
  `;
}

/**
 * Renderiza o card de um único grupo.
 * @param {{ nome: string, classificacao: object[] }} grupo
 * @returns {string} HTML
 */
function renderGrupoCard({ nome, classificacao }) {
  const linhas = classificacao.map((c, k) => renderLinhaTime(c, k)).join('');
  return `
    <div class="grupo-card">
      <div class="grupo-titulo">Grupo ${nome}</div>
      <table class="tabela-grupo">
        <colgroup>
          <col class="col-pos">
          <col class="col-time">
          <col class="col-pts">
        </colgroup>
        <thead>
          <tr>
            <th>#</th>
            <th class="col-time">Time</th>
            <th>Pts</th>
          </tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>
  `;
}

/**
 * Renderiza uma linha de time na tabela de classificação.
 * @param {object} c         — dados do time
 * @param {number} posicao   — posição 0-based na tabela
 * @returns {string} HTML
 */
function renderLinhaTime(c, posicao) {
  const sg           = c.sg > 0 ? `+${c.sg}` : c.sg;
  const classificado = posicao < 2 ? ' class="classificado"' : '';
  const jogador      = c.jogador
    ? `<span class="td-jogador">(${c.jogador})</span>` : '';

  return `
    <tr${classificado}>
      <td>${posicao + 1}</td>
      <td class="col-time">
        <div class="td-time-inner">
          <div class="td-logo">
            <img src="/img/${slugLogo(c.time)}.png" alt="${c.time}">
          </div>
          <span class="td-nome">${c.time}</span>
          ${jogador}
        </div>
      </td>
      <td class="col-pts">${c.pontos}</td>
    </tr>
  `;
}

/* ══════════════════════════════════════════════════════════════
   BRACKET
══════════════════════════════════════════════════════════════ */

/**
 * Extrai o vencedor de um jogo se já houver placar definido.
 * @param {object} jogo
 * @returns {string|null}
 */
function extrairVencedor(jogo) {
  if (!jogo || jogo.gols1 === null || jogo.gols1 === undefined ||
               jogo.gols2 === null || jogo.gols2 === undefined) return null;
  if (jogo.gols1 > jogo.gols2) return jogo.time1;
  if (jogo.gols2 > jogo.gols1) return jogo.time2;
  return null; // empate — sem vencedor ainda
}

/**
 * Normaliza a lista de jogos em um objeto indexado por fase,
 * preenchendo com slots vazios quando necessário e propagando
 * vencedores já confirmados para as fases seguintes.
 * @param {object[]} jogos
 * @returns {Record<string, object[]>}
 */
function normalizarBracket(jogos) {
  const porFase = Object.fromEntries(BRACKET.FASES.map((f) => [f, []]));

  for (const jogo of jogos) {
    if (porFase[jogo.fase]) porFase[jogo.fase].push(jogo);
  }

  const jogoVazio = (fase) => ({
    fase, time1: null, time2: null, gols1: null, gols2: null, status: null,
  });

  for (const [fase, qtd] of Object.entries(BRACKET.ESTRUTURA)) {
    while (porFase[fase].length < qtd) porFase[fase].push(jogoVazio(fase));
    porFase[fase] = porFase[fase].slice(0, qtd);
  }

  // Propagação de vencedores: oitavas → quartas → semi → final
  const sequencia = [
    { de: 'oitavas', para: 'quartas' },
    { de: 'quartas', para: 'semi'    },
    { de: 'semi',    para: 'final'   },
  ];

  for (const { de, para } of sequencia) {
    const origem  = porFase[de];
    const destino = porFase[para];

    // Lado esquerdo: pares 0-1 → slot 0, pares 2-3 → slot 1
    // Lado direito:  pares 4-5 → slot 2, pares 6-7 → slot 3  (só em oitavas)
    // Para quartas→semi e semi→final, a divisão é sempre par de dois em dois.
    const metade = Math.floor(origem.length / 2);

    for (let i = 0; i < destino.length; i++) {
      const jA = origem[i * 2]     ?? null;
      const jB = origem[i * 2 + 1] ?? null;
      const vA = extrairVencedor(jA);
      const vB = extrairVencedor(jB);

      // Só preenche se o slot de destino ainda não tem o time definido no payload
      if (!destino[i].time1 && vA) destino[i].time1 = vA;
      if (!destino[i].time2 && vB) destino[i].time2 = vB;
    }
  }

  return porFase;
}

/**
 * Gera uma linha SVG entre dois pontos.
 * @returns {string} elemento SVG <line>
 */
function svgLine(x1, y1, x2, y2) {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
    stroke="${BRACKET.STROKE}" stroke-width="${BRACKET.STROKE_W}"/>`;
}

/**
 * Gera as linhas conectoras entre duas colunas adjacentes do bracket.
 * @param {number} nA    — nº de slots na coluna de origem
 * @param {number} colA  — índice da coluna de origem
 * @param {number} nB    — nº de slots na coluna de destino
 * @param {number} colB  — índice da coluna de destino
 * @param {'r'|'l'} dir  — direção: 'r' para esquerda→direita, 'l' para direita→esquerda
 * @returns {string} SVG
 */
function geraLinhas(nA, colA, nB, colB, dir) {
  const xA = dir === 'r' ? colX(colA) + BRACKET.COL_W : colX(colA);
  const xB = dir === 'r' ? colX(colB)                  : colX(colB) + BRACKET.COL_W;
  const xM = (xA + xB) / 2;
  const off = BRACKET.LBL_H;

  return Array.from({ length: nA / 2 }, (_, i) => {
    const yA1 = off + slotCY(nA, i * 2);
    const yA2 = off + slotCY(nA, i * 2 + 1);
    const yBc = off + slotCY(nB, i);
    return [
      svgLine(xA, yA1, xM, yA1),
      svgLine(xA, yA2, xM, yA2),
      svgLine(xM, yA1, xM, yA2),
      svgLine(xM, yBc, xB, yBc),
    ].join('');
  }).join('');
}

/**
 * Gera todas as linhas conectoras do bracket completo.
 * @returns {string} SVG
 */
function gerarTodasLinhas() {
  const off = BRACKET.LBL_H;
  return [
    // Lado esquerdo: oitavas → quartas → semi → final
    geraLinhas(4, 0, 2, 1, 'r'),
    geraLinhas(2, 1, 1, 2, 'r'),
    svgLine(colX(2) + BRACKET.COL_W, off + slotCY(1, 0), colX(3), off + slotCY(1, 0)),
    // Lado direito: oitavas → quartas → semi → final
    geraLinhas(4, 6, 2, 5, 'l'),
    geraLinhas(2, 5, 1, 4, 'l'),
    svgLine(colX(4), off + slotCY(1, 0), colX(3) + BRACKET.COL_W, off + slotCY(1, 0)),
  ].join('');
}

/**
 * Renderiza um confronto (par de time-boxes) na posição absoluta correta.
 * @param {object}   jogo
 * @param {number}   colIdx   — índice da coluna
 * @param {number}   slotIdx  — índice do slot na coluna
 * @param {number}   nSlots   — total de slots na coluna
 * @param {string[]} buffer   — array de HTML acumulado
 */
function renderConfronto(jogo, colIdx, slotIdx, nSlots, buffer) {
  const cy     = slotCY(nSlots, slotIdx);
  const top    = BRACKET.LBL_H + cy - CONF_H / 2;
  const x      = colX(colIdx);
  const aoVivo = jogo.status === 'em_andamento';

  const temPlacar = jogo.gols1 !== null && jogo.gols1 !== undefined &&
                    jogo.gols2 !== null && jogo.gols2 !== undefined;
  const v1 = temPlacar && jogo.gols1 > jogo.gols2;
  const v2 = temPlacar && jogo.gols2 > jogo.gols1;

  // Eliminado = perdedor confirmado (jogo encerrado e há um vencedor claro)
  const encerrado = jogo.status === 'encerrado' || (!aoVivo && temPlacar && (v1 || v2));
  const e1 = encerrado && !v1 && v2;
  const e2 = encerrado && !v2 && v1;

  buffer.push(`
    <div style="position:absolute;top:${top}px;left:${x}px;width:${BRACKET.COL_W}px;">
      ${renderTimeBox(jogo.time1, jogo.gols1, v1, aoVivo, e1)}
      <div style="height:${BRACKET.BOX_GAP}px;"></div>
      ${renderTimeBox(jogo.time2, jogo.gols2, v2, aoVivo, e2)}
    </div>
  `);
}

/**
 * Renderiza o box visual de um time dentro de um confronto.
 * @param {string|null} nome
 * @param {number|null} gols
 * @param {boolean}     venceu
 * @param {boolean}     aoVivo
 * @param {boolean}     eliminado — perdedor confirmado (jogo encerrado)
 * @returns {string} HTML
 */
function renderTimeBox(nome, gols, venceu, aoVivo, eliminado) {
  if (!nome) {
    return `<div class="time-box vazio"><span class="box-nome">a definir</span></div>`;
  }

  let cls;
  if (aoVivo)      cls = 'time-box em-jogo';
  else if (venceu) cls = 'time-box vencedor';
  else if (eliminado) cls = 'time-box eliminado';
  else             cls = 'time-box';

  const placar = gols !== null && gols !== undefined ? gols : '';

  return `
    <div class="${cls}">
      <div class="box-logo"><img src="/img/${slugLogo(nome)}.png" alt="${nome}"></div>
      <span class="box-nome">${nome}</span>
      <span class="box-gols">${placar}</span>
    </div>
  `;
}

/**
 * Renderiza o bracket completo de mata-mata.
 * @param {object[]} jogos
 * @returns {string} HTML
 */
function renderBracket(jogos) {
  const pf = normalizarBracket(jogos);

  // Divisão esquerda/direita do bracket
  const esqOit = pf.oitavas.slice(0, 4);
  const esqQua = pf.quartas.slice(0, 2);
  const esqSem = pf.semi.slice(0, 1);
  const dirOit = pf.oitavas.slice(4);
  const dirQua = pf.quartas.slice(2);
  const dirSem = pf.semi.slice(1);
  const jFinal = pf.final[0];

  const totalH = BRACKET.LBL_H + BRACKET.BR_H;
  const buffer = [];

  // Labels de fase
  for (const [colIdx, label] of BRACKET.LABELS) {
    buffer.push(`
      <div class="br-label" style="left:${colX(colIdx)}px;width:${BRACKET.COL_W}px;">
        ${label}
      </div>
    `);
  }

  // Confrontos por coluna
  esqOit.forEach((j, i) => renderConfronto(j, 0, i, 4, buffer));
  esqQua.forEach((j, i) => renderConfronto(j, 1, i, 2, buffer));
  renderConfronto(esqSem[0], 2, 0, 1, buffer);
  renderConfronto(jFinal,    3, 0, 1, buffer);
  renderConfronto(dirSem[0], 4, 0, 1, buffer);
  dirQua.forEach((j, i) => renderConfronto(j, 5, i, 2, buffer));
  dirOit.forEach((j, i) => renderConfronto(j, 6, i, 4, buffer));

  // Label "Campeão" abaixo da final
  const cTop = BRACKET.LBL_H + slotCY(1, 0) + CONF_H / 2 + 12;
  buffer.push(`
    <div class="br-campeon" style="left:${colX(3)}px;top:${cTop}px;width:${BRACKET.COL_W}px;">
      Campeão
    </div>
  `);

  return `
    <div class="bracket-wrap" style="width:${TOTAL_W}px;height:${totalH}px;">
      <svg>${gerarTodasLinhas()}</svg>
      ${buffer.join('')}
    </div>
  `;
}

/* ──────────────────────────────────────────────
   INICIALIZAÇÃO
────────────────────────────────────────────── */

conectar();