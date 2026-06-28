// ── SSE ───────────────────────────────────────────────────────────────────

let sse = null;

function conectar() {
  if (sse) sse.close();

  sse = new EventSource('/stream/aovivo');

  sse.onmessage = (e) => render(JSON.parse(e.data));

  sse.onerror = () => {
    sse.close();
    setTimeout(conectar, 3000);
  };
}

// ── UTILITÁRIOS ───────────────────────────────────────────────────────────

function slugLogo(nome) {
  return nome
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');
}

function criarElemento(tag, classes = [], atributos = {}) {
  const el = document.createElement(tag);
  if (classes.length) el.className = classes.join(' ');
  for (const [k, v] of Object.entries(atributos)) el.setAttribute(k, v);
  return el;
}

// ── MATA-MATA ─────────────────────────────────────────────────────────────

const SIZES = {
  1: 'size-1',
  2: 'size-2',
  4: 'size-4',
  8: 'size-8',
};

function resolverChave(total) {
  return [1, 2, 4, 8].find((k) => k >= total) ?? 8;
}

function classeTime(match, isT1) {
  const hasScore = match.s1 !== null && match.s2 !== null;
  const losing   = isT1 ? (hasScore && match.s2 > match.s1) : (hasScore && match.s1 > match.s2);
  const winning  = isT1 ? (hasScore && match.s1 > match.s2) : (hasScore && match.s2 > match.s1);

  const classes = ['team'];

  if (match.status === 'encerrado' && losing)  classes.push('eliminado');
  if (match.status === 'encerrado' && winning) classes.push('winner');
  if (match.status === 'em_jogo'   && losing)  classes.push('perdendo');
  if (match.status === 'em_jogo'   && winning) classes.push('winner');

  return classes;
}

function buildRow(match, nome, score, isT1) {
  const row = criarElemento('div', [...classeTime(match, isT1), isT1 ? 'team--top' : 'team--bot']);

  const logoWrap = criarElemento('div', ['tlogo']);
  const img = criarElemento('img', [], { src: `/img/${slugLogo(nome)}.png`, alt: '' });
  logoWrap.appendChild(img);

  const nomeEl  = criarElemento('span', ['tname']);
  nomeEl.textContent = nome || '—';

  const scoreEl = criarElemento('span', ['tscore']);
  scoreEl.textContent = score !== null && score !== undefined ? score : '';

  row.append(logoWrap, nomeEl, scoreEl);
  return row;
}

function buildCell(match, sizeClass) {
  const cell = criarElemento('div', ['cell']);
  if (!match) return cell;

  const hasScore = match.s1 !== null && match.s2 !== null;
  const sc1 = hasScore ? match.s1 : null;
  const sc2 = hasScore ? match.s2 : null;

  const matchEl = criarElemento('div', ['match', sizeClass]);
  matchEl.append(
    buildRow(match, match.t1, sc1, true),
    buildRow(match, match.t2, sc2, false),
  );

  cell.appendChild(matchEl);
  return cell;
}

function renderMataMata(dados) {
  const root = document.getElementById('root');

  if (!dados.partidas?.length) {
    root.innerHTML = '';
    return;
  }

  const matches   = dados.partidas;
  const chave     = resolverChave(matches.length);
  const sizeClass = SIZES[chave];

  const wrap = criarElemento('div', ['wrap']);

  if (dados.fase) {
    const faseTopo = criarElemento('div', ['fase-topo']);
    faseTopo.textContent = dados.fase;
    wrap.appendChild(faseTopo);
  }

  const total = matches.length;

  if (total === 1) {
    const half = criarElemento('div', ['half', 'half--center']);
    half.appendChild(buildCell(matches[0], sizeClass));
    wrap.appendChild(half);
  } else if (total === 2) {
    const half = criarElemento('div', ['half', 'half--center']);
    matches.forEach((m) => half.appendChild(buildCell(m, sizeClass)));
    wrap.appendChild(half);
  } else {
    const mid  = Math.ceil(total / 2);
    const top  = matches.slice(0, mid);
    const bot  = matches.slice(mid);
    while (bot.length < top.length) bot.push(null);

    const halfTop = criarElemento('div', ['half']);
    top.forEach((m) => halfTop.appendChild(buildCell(m, sizeClass)));

    const divider = criarElemento('div', ['divider']);

    const halfBot = criarElemento('div', ['half']);
    bot.forEach((m) => halfBot.appendChild(buildCell(m, sizeClass)));

    wrap.append(halfTop, divider, halfBot);
  }

  root.innerHTML = '';
  root.appendChild(wrap);
}

// ── FASE DE GRUPOS ────────────────────────────────────────────────────────

function capturarPosicoesAntigas() {
  const mapa = {};
  document.querySelectorAll('.tabela-grupo tbody tr').forEach((tr) => {
    if (tr.dataset.time) mapa[tr.dataset.time] = tr.getBoundingClientRect().top;
  });
  return mapa;
}

function animarLinhas(posicoesAntigas) {
  const thHash  = document.querySelector('.tabela-grupo thead th');
  const slideX  = thHash ? thHash.getBoundingClientRect().width / 2 : 20;

  const linhasMovendo = [];

  document.querySelectorAll('.tabela-grupo tbody tr').forEach((tr) => {
    const antiga = posicoesAntigas[tr.dataset.time];
    if (!antiga) return;

    const delta = antiga - tr.getBoundingClientRect().top;
    if (delta !== 0) linhasMovendo.push({ tr, delta });
  });

  if (!linhasMovendo.length) return;

  linhasMovendo.forEach(({ tr, delta }) => {
    tr.style.transition = 'none';
    tr.style.transform  = `translate(0px, ${delta}px)`;
    tr.style.position   = 'relative';
    tr.style.zIndex     = '10';
  });

  linhasMovendo[0].tr.getBoundingClientRect(); // força reflow

  linhasMovendo.forEach(({ tr, delta }) => {
    tr.style.transition = 'transform 700ms cubic-bezier(0.4, 0, 1, 1)';
    tr.style.transform  = `translate(-${slideX}px, ${delta}px)`;
  });

  setTimeout(() => {
    linhasMovendo.forEach(({ tr }) => {
      tr.style.transition = 'transform 800ms cubic-bezier(0.4, 0, 0.2, 1)';
      tr.style.transform  = `translate(-${slideX}px, 0px)`;
    });

    setTimeout(() => {
      linhasMovendo.forEach(({ tr }) => {
        tr.style.transition = 'transform 700ms cubic-bezier(0, 0, 0.3, 1)';
        tr.style.transform  = 'translate(0px, 0px)';
      });

      setTimeout(() => {
        linhasMovendo.forEach(({ tr }) => {
          tr.style.transition = '';
          tr.style.transform  = '';
          tr.style.position   = '';
          tr.style.zIndex     = '';
        });
      }, 700);
    }, 800);
  }, 700);
}

function buildLinhaGrupo(classificacao, index) {
  const { time, em_jogo, sg, pontos, v, e, d, gp, gc, jogador } = classificacao;

  const tr = criarElemento('tr', em_jogo ? ['em-jogo'] : []);
  tr.dataset.time = time;

  const sgFormatado = sg > 0 ? `+${sg}` : sg;

  const tdPos = criarElemento('td');
  tdPos.textContent = index + 1;

  const tdTime = criarElemento('td', ['col-time']);
  const inner  = criarElemento('div', ['td-time-inner']);
  const tdLogo = criarElemento('div', ['td-logo']);
  const img    = criarElemento('img', [], { src: `/img/${slugLogo(time)}.png`, alt: '' });
  tdLogo.appendChild(img);

  const tdNome = criarElemento('span', ['td-nome']);
  tdNome.textContent = time;

  inner.append(tdLogo, tdNome);

  if (jogador) {
    const tdJogador = criarElemento('span', ['td-jogador']);
    tdJogador.textContent = `(${jogador})`;
    inner.appendChild(tdJogador);
  }

  tdTime.appendChild(inner);

  const cellsPts = [pontos, v, e, d, gp, gc, sgFormatado];
  const classesPts = ['col-pts', '', '', '', '', '', ''];

  const tdPts = cellsPts.map((val, i) => {
    const td = criarElemento('td', classesPts[i] ? [classesPts[i]] : []);
    td.textContent = val;
    return td;
  });

  tr.append(tdPos, tdTime, ...tdPts);
  return tr;
}

function renderGrupo(dados) {
  const root = document.getElementById('root');
  const g = dados.grupo;

  if (!g) {
    root.innerHTML = '';
    return;
  }

  const posicoesAntigas = capturarPosicoesAntigas();

  const tabela = criarElemento('table', ['tabela-grupo']);

  const colgroup = document.createElement('colgroup');
  ['col-pos', 'col-time', 'col-pts', 'col-ved', 'col-ved', 'col-ved', 'col-gol', 'col-gol', 'col-gol'].forEach((cls) => {
    colgroup.appendChild(criarElemento('col', [cls]));
  });

  const thead = document.createElement('thead');
  const tr    = document.createElement('tr');
  ['#', 'Time', 'Pts', 'V', 'E', 'D', 'GP', 'GC', 'SG'].forEach((txt, i) => {
    const th = criarElemento('th', i === 1 ? ['col-time'] : []);
    th.textContent = txt;
    tr.appendChild(th);
  });
  thead.appendChild(tr);

  const tbody = document.createElement('tbody');
  g.classificacao.forEach((c, i) => tbody.appendChild(buildLinhaGrupo(c, i)));

  tabela.append(colgroup, thead, tbody);

  root.innerHTML = '';
  root.appendChild(tabela);

  requestAnimationFrame(() => animarLinhas(posicoesAntigas));
}

// ── ROTEADOR ──────────────────────────────────────────────────────────────

function render(dados) {
  if (Array.isArray(dados.partidas)) {
    renderMataMata(dados);
  } else {
    renderGrupo(dados);
  }
}

conectar();