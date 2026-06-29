<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/python-3.10%2B-orange" alt="Python">
  <img src="https://img.shields.io/badge/langgraph-0.2%2B-purple" alt="LangGraph">
</p>

<br>

<p align="center">
  <img src="https://via.placeholder.com/200x200/0A0A0F/00FF88?text=🧠" alt="Mega Brain" width="200" height="200" style="border-radius: 20px;">
</p>

<h1 align="center">🧠 Mega Brain v2</h1>

<p align="center">
  <strong>Sistema Multi-Agente com LangGraph</strong><br>
  Roteamento inteligente, squad de agentes paralelos e StateGraph
</p>

<p align="center">
  <i>A mágica é arquitetura, não feitiço.</i>
</p>

<br>

---

## 📋 Sobre

O **Mega Brain v2** é uma reescrita completa do sistema de orquestração multi-agente usando **LangGraph**. A versão v1 (Python puro) está na branch [`v1-legacy`](https://github.com/generalrodolfao/mega-brain/tree/v1-legacy).

- 🔀 **Roteamento inteligente** — 4 níveis (fast, standard, premium, squad) baseado em keywords + LLM
- 🧭 **StateGraph** — Nós e arestas condicionais com estado tipado
- 👥 **Squad paralelo** — Até 6 agentes especializados executando em paralelo com consolidação
- 📊 **Servidor HTTP + WebSocket** — API REST e streaming em tempo real

---

## 🏗 Arquitetura (LangGraph StateGraph)

```
                        ┌──────────────────┐
                        │   User Input      │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ analyze_sentiment │
                        │ (emoji/positivo/  │
                        │  neutro/negativo) │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ detect_complexity │
                        │ (simple/medium/   │
                        │  complex)         │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  decide_route     │
                        │  ┌─────────────┐  │
                        │  │ FAST        │──┼──→ respond_fast
                        │  │ STANDARD    │──┼──→ respond_standard
                        │  │ PREMIUM     │──┼──→ respond_premium
                        │  │ SQUAD       │──┼──→ squad_fanout
                        │  └─────────────┘  │     ├─ copywriter
                        └──────────────────┘     ├─ strategist
                                                  ├─ social_media
                                                  ├─ seo
                                                  ├─ designer
                                                  └─ reviewer
                                                       │
                                                       ▼
                                                  squad_consolidate
```

---

## 🚀 Quick Start

### 1. Clone e instale

```bash
git clone https://github.com/generalrodolfao/mega-brain.git
cd mega-brain/megabrain_v2
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edite .env com sua OPENROUTER_API_KEY
```

### 3. Execute

```bash
# Demo com 3 exemplos (simples, médio, complexo)
python main.py

# Servidor HTTP + WebSocket
python server.py
# Abra http://localhost:8701
```

---

## 🧪 Como o Router decide?

| Gatilho | Rota | Modelo |
|---------|------|--------|
| "Qual a data e hora?" | `fast` | Gemini 2.5 Flash Lite |
| "Brain, cria estratégia..." | `standard` | GPT-4o |
| "Análise profunda do mercado..." | `premium` | Claude Sonnet 4 |
| "Mega Brain, ative o squad..." | `squad` | Squad paralelo (6 agentes) |

### Teste via API

```bash
curl -X POST http://localhost:8701/api/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Mega Brain, crie uma campanha completa"}'
```

---

## 📂 Estrutura do Projeto

```
mega-brain/
├── README.md
├── .gitignore
├── docs/                          # GitHub Pages — hub de materiais
│   ├── index.html
│   ├── slides-mega-brain.pdf
│   └── slides-cafe-dados.pdf
│
├── slides-mega-brain.html         # Apresentação: arquitetura
├── slides-cafe-dados.html         # Apresentação: Café com Dados #5
│
└── megabrain_v2/                  # Código principal (LangGraph)
    ├── main.py                    # Demo interativa
    ├── server.py                  # Servidor HTTP + WebSocket
    ├── graph.py                   # StateGraph (nós + arestas)
    ├── state.py                   # AgentState (TypedDict)
    ├── config.py                  # Modelos, keywords, agentes
    ├── requirements.txt           # Dependências
    ├── nodes/
    │   ├── classify.py            # Análise de sentimento/complexidade/rota
    │   ├── respond.py             # Respostas por tier (fast/standard/premium)
    │   ├── squad.py               # Fan-out paralelo + consolidação
    │   └── tools.py               # Ferramentas (get_time, calculate, web_search)
    ├── guias/                     # Guias PDF e Markdown
    └── ilustracoes/               # Diagramas SVG dos conceitos
```

---

## 📚 Documentos

- **[Hub de Materiais](https://generalrodolfao.github.io/mega-brain/)** — GitHub Pages com ilustrações, guias, slides e demos
- **[slides-mega-brain.html](slides-mega-brain.html)** — 16 slides sobre arquitetura
- **[slides-cafe-dados.html](slides-cafe-dados.html)** — Apresentação Café com Dados #5
- **[Ilustrações SVG](megabrain_v2/ilustracoes/)** — Tokenização, Attention, Embeddings, RAG, Tool Calling, Agent Loop
- **[Guias PDF](megabrain_v2/guias/)** — Setup LangChain, Primeiro Projeto, Intro LangGraph

### Branch v1-legacy

A versão original (Python puro, sem LangGraph) está em [`v1-legacy`](https://github.com/generalrodolfao/mega-brain/tree/v1-legacy) — com suporte a voz (Whisper STT), dashboard Pixi.js e Copy Chief Squad em YAML.

---

## 📜 Licença

MIT — use, modifique, venda o serviço, não o hype.

---

<p align="center">
  <strong>🧠 O verdadeiro Mega Brain é o código que você escreve.</strong>
</p>
