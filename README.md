# FIFA 16 OBS Layout

Layout interativo para OBS inspirado no estilo visual do FIFA 16. Exibe placar ao vivo e tabela de grupos em janelas de browser separadas, lendo o placar diretamente da memória do processo do jogo.

---

## Tecnologias

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Qt6-41CD52?style=flat&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-banco%20local-003B57?style=flat&logo=sqlite&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-layout-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-estilo-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-SSE-F7DF1E?style=flat&logo=javascript&logoColor=black)
![pymem](https://img.shields.io/badge/pymem-leitura%20de%20memória-red?style=flat)

- **PySide6** — interface desktop para gerenciar torneios e partidas
- **Python HTTP + SSE** — servidor local na porta 8000 que envia atualizações em tempo real via Server-Sent Events
- **pymem** — lê o placar e nomes dos times diretamente do processo `fifa16.exe`
- **SQLite** — persiste torneios, grupos, jogos e classificação localmente
- **HTML / CSS / JS** — páginas do overlay consumidas pelo OBS como Browser Source

---

## Instalação

**Pré-requisitos:** Python 3.12 ou superior, FIFA 16 instalado no Windows.

```bash
# 1. Clone ou extraia o projeto
git clone https://github.com/seu-usuario/fifa16-obs-layout.git
cd fifa16-obs-layout

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute
python main.py
```

Na primeira execução, o assistente vai guiar a criação do torneio (nome, times, formato).  
A partir da segunda execução, você pode carregar um torneio já existente.

Ao iniciar a primeira partida, o navegador abre automaticamente as duas páginas do overlay.

---

## Configuração no OBS

Adicione duas **Browser Sources** no OBS com as seguintes dimensões:

| Janela | URL | Resolução |
|---|---|---|
| Placar ao vivo | `http://localhost:8000/aovivo` | **1010 × 300** |
| Tabela de grupos | `http://localhost:8000/grupos` | **1600 × 1300** |

> Marque a opção **"Refresh browser when scene becomes active"** em cada fonte para garantir que o overlay reconecte caso o servidor seja reiniciado.

---

## Configuração dos offsets de memória (`settings.json`)

O arquivo `settings.json` contém os offsets usados para ler o placar da memória do FIFA 16. **Ele já vem pré-configurado para o FIFA 16**, então na maioria dos casos não é necessário alterar nada.

```json
{
  "home_goals_offset": 55489624,
  "away_goals_offset": 55489628,
  "home_team_offset":  55546284,
  "away_team_offset":  55546436
}
```

Caso o layout não esteja lendo o placar corretamente (por conta de patch ou versão diferente do executável), vá em **Opções → Configurações de memória** dentro do aplicativo e atualize os offsets manualmente.

Os endereços de imagem das bandeiras e escudos dos times também ficam na pasta `static/img/` — caso queira substituir alguma imagem, basta colocar o arquivo com o mesmo nome.

---

## Estrutura do projeto

```
.
├── main.py               # ponto de entrada
├── requirements.txt
├── settings.json         # offsets de memória do FIFA 16
├── data/
│   └── torneio.db        # banco SQLite (gerado automaticamente)
├── app/
│   ├── database.py
│   ├── engine.py         # lógica de grupos e mata-mata
│   ├── memory.py         # leitura de memória via pymem
│   ├── models.py
│   ├── server.py         # HTTP server + SSE
│   ├── state.py
│   ├── times.py          # catálogo de times e IDs
│   └── ui/               # janelas PySide6
└── static/
    ├── aovivo.html        # overlay do placar
    ├── grupos.html        # overlay da tabela
    ├── css/
    ├── js/
    └── img/              # bandeiras e escudos
```