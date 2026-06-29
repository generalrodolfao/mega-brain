<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/python-3.10%2B-orange" alt="Python">
</p>

<br>

<p align="center">
  <img src="https://via.placeholder.com/200x200/0A0A0F/00FF88?text=🧠" alt="Mega Brain" width="200" height="200" style="border-radius: 20px;">
</p>

<h1 align="center">🧠 Mega Brain</h1>

<p align="center">
  <strong>Sistema Multi-Agente de Orquestração de IA</strong><br>
  Com reconhecimento de voz, roteamento inteligente e dashboard em tempo real
</p>

<p align="center">
  <i>A versão que funciona — open-source, extensível, sem hype.</i>
</p>

<br>

---

## 📋 Sobre

O **Mega Brain** é um sistema de orquestração multi-agente que:

- 🎤 **Reconhece voz** via Whisper STT
- 🧠 **Roteia inteligentemente** entre modelos (Gemini Flash, GPT-4o, Claude Opus)
- 👥 **Ativa squads de agentes** especializados (o "Copy Chief")
- 📊 **Visualiza em tempo real** com dashboard Pixi.js animado

Foi construído como resposta técnica ao hype do "Mega Brain" do Thiago Finch — mostrando que a tecnologia é real, o marketing é que era exagerado.

> **A mágica é arquitetura, não feitiço.**

---

## 🏗 Arquitetura

```
                    ┌─────────────────────┐
                    │   Voice Gateway      │
                    │  (Whisper STT)       │
                    └────────┬────────────┘
                             │ áudio transcrito
                             ▼
                    ┌─────────────────────┐
                    │  Sentiment Router    │
                    │  Classifica intenção │
                    │  e complexidade      │
                    └────────┬────────────┘
                             │ nível detectado
                             ▼
        ┌─────────────────────────────────────────┐
        │           Model Router                   │
        │  "normal"     → Gemini Flash (barato)    │
        │  "brain"      → GPT-4o (intermediário)   │
        │  "mega brain" → Claude Opus (topo)       │
        └─────────────────────────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │     Copy Chief Squad (7 agentes)         │
        │                                         │
        │  👑 Copy Chief   → Coordenador          │
        │  📊 Strategist   → Estratégia           │
        │  ✍️ Copywriter   → Redação              │
        │  📱 Social Media → Redes sociais        │
        │  🎨 Designer     → Briefing visual      │
        │  🔍 SEO/Media    → Distribuição         │
        │  ✅ Reviewer     → Qualidade            │
        └─────────────────────────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │     Dashboard Pixi.js (WebSocket)        │
        │   Visualização em tempo real             │
        │   "Mega Brain ativado" animação          │
        └─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Instalação

```bash
git clone https://github.com/seu-usuario/mega-brain.git
cd mega-brain
pip install -r requirements.txt
```

### 2. Configuração

```bash
cp .env.example .env
# Edite .env com suas chaves de API
```

### 3. Executar

```bash
# Modo interativo (texto)
python main.py

# Modo roteamento direto
python main.py route -t "Mega Brain, cria uma estratégia de lançamento"

# Dashboard com animação
python main.py server
# Abra http://localhost:3001

# Demonstração automática
python main.py demo
```

---

## 🧪 Demonstração do Router

```python
from core.router import route, format_route_output

# Entrada simples → modelo econômico
decision = route("Qual a previsão do tempo?")
print(format_route_output(decision))
# 💬 NORMAL → gemini-2.0-flash-lite

# Menção a "brain" → modelo intermediário
decision = route("Brain, cria um post para o LinkedIn")
print(format_route_output(decision))
# ⚡ BRAIN → gpt-4o

# "Mega Brain" → modelo topo + squad completo
decision = route("Mega Brain, ative o Copy Chief para uma campanha")
print(format_route_output(decision))
# 🧠 MEGA BRAIN → claude-sonnet-4 + squad copy-chief
```

---

## 👥 Copy Chief Squad

O **Copy Chief** é um squad de 7 agentes especializados em marketing e copywriting:

| Agente | Modelo | Função |
|--------|--------|--------|
| 👑 Copy Chief | Claude Sonnet | Coordena, delega, revisa |
| 📊 Strategist | GPT-4o | Estratégia, posicionamento, público |
| ✍️ Copywriter | Claude Sonnet | Redação, headlines, storytelling |
| 📱 Social Media | GPT-4o mini | Adaptação por plataforma |
| 🎨 Designer Text | Gemini Flash | Briefing visual |
| 🔍 SEO/Media | GPT-4o mini | Distribuição e SEO |
| ✅ Reviewer | Claude Sonnet | Qualidade e consistência |

Cada agente tem `system_prompt`, modelo e ferramentas específicas definidos em `squads/copy-chief/agents/`.

---

## 📂 Estrutura do Projeto

```
mega-brain/
├── main.py                      # Entry point (CLI interativa)
├── router.py                    # Router independente (demo)
├── .env.example                 # Configuração de API keys
├── requirements.txt             # Dependências
├── README.md                    # Esta documentação
│
├── core/
│   ├── __init__.py
│   ├── engine.py                # Orchestrator, StateManager, Agent, Squad
│   ├── router.py                # Sentiment + Model Router
│   ├── server.py                # WebSocket + HTTP server
│   └── voice.py                 # Whisper STT integration
│
├── dashboard/
│   └── index.html               # Pixi.js dashboard animado
│
├── squads/
│   └── copy-chief/
│       ├── squad.yaml           # Definição do squad
│       ├── pipeline.yaml        # Pipeline de execução
│       └── agents/              # Definição individual dos agentes
│           ├── copy-chief.yaml
│           ├── strategist.yaml
│           ├── copywriter.yaml
│           ├── social-media.yaml
│           ├── designer-text.yaml
│           ├── seo-media.yaml
│           └── reviewer.yaml
│
├── roteiro-mega-brain.md        # Roteiro para vídeo YouTube
├── slides-mega-brain.html       # Apresentação de slides (arquitetura)
├── slides-cafe-dados.html       # Apresentação "Café com Dados #5"
│
├── megabrain_v2/                # Reescrita com LangGraph
│   ├── graph.py                 # StateGraph de orquestração
│   ├── nodes/                   # Nós: classify, respond, squad, tools
│   └── ilustracoes/             # Diagramas SVG da arquitetura
│
└── audio/                       # Áudio de referência para voice clone
```

---

## 🔬 Comparação: Mega Brain vs. Concorrentes

| Funcionalidade | Mega Brain (aqui) | Mega Brain (Finch) | Opensquad |
|---------------|-------------------|-------------------|-----------|
| Preço | 🆓 Open-source | 💰 Pago (Pro) | 🆓 Open-source |
| Reconhecimento de voz | ✅ Whisper STT | ❌ CLI only | ❌ CLI only |
| Router inteligente | ✅ 3 níveis | ❌ Fixo | ❌ Fixo |
| Squad multi-agente | ✅ Copy Chief (7) | ✅ Copy Chief | ✅ Squads YAML |
| Dashboard | ✅ Pixi.js animado | ✅ state.json | ✅ Pixi.js + Zustand |
| Pipeline | ✅ YAML + Python | ✅ YAML + Node | ✅ YAML + Markdown |
| Código aberto | ✅ MIT | ⚠️ Fork do aiox-core | ✅ MIT |

---

## 📚 Documentos

### Roteiro para Vídeo
- **[roteiro-mega-brain.md](roteiro-mega-brain.md)** — Roteiro completo para vídeo YouTube (~17 min), analisando tecnicamente o Mega Brain do Thiago Finch. Inclui timestamps, visuais, comparações e argumentário.

### Apresentações
- **[slides-mega-brain.html](slides-mega-brain.html)** — 16 slides em dark mode com navegação por teclado. Arquitetura, demonstração técnica, comparação de mercado.
- **[slides-cafe-dados.html](slides-cafe-dados.html)** — Apresentação "Café com Dados #5: Construindo um Mega Brain com IA". Slides interativos com Chart.js para palestras e meetups.

### Arquitetura v2 (LangGraph)
- **[megabrain_v2/](megabrain_v2/)** — Reescrita do sistema usando LangGraph com state-machine para orquestração multi-agente.
- **[megabrain_v2/ilustracoes/](megabrain_v2/ilustracoes/)** — Diagramas SVG: tokenization, attention, embeddings, RAG, tool calling, agent loop.

### Demo
- **Demo ao vivo** com `python main.py demo`
- **Dashboard animado** com `python main.py server`

---

## 🎥 Para Criadores de Conteúdo

Este repositório foi projetado para ser usado em vídeos de análise técnica:

1. **Roteiro completo** em [roteiro-mega-brain.md](roteiro-mega-brain.md) (~17 min de vídeo)
2. **Slides** em [slides-mega-brain.html](slides-mega-brain.html) (16 slides, dark mode, navegação por teclado)
3. **Demo ao vivo** com `python main.py demo`
4. **Dashboard animado** com `python main.py server`

---

## 📜 Licença

MIT — use, modifique, venda o serviço, não o hype.

---

<p align="center">
  <strong>🧠 O verdadeiro Mega Brain é o código que você escreve.</strong>
</p>
