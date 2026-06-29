# Guia Rápido: Setup LangChain + LangGraph

## 1. Ambiente Virtual

```bash
# Criar
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Confirmar
which python   # deve mostrar .venv/bin/python
python --version
```

## 2. Instalar Dependências

```bash
# Core
pip install langgraph langchain-core langchain-openai

# Úteis
pip install httpx python-dotenv aiohttp

# Tudo de uma vez
pip install langgraph langchain-core langchain-openai httpx python-dotenv aiohttp
```

## 3. Configurar API Key

```bash
# Criar .env
echo 'OPENROUTER_API_KEY=sk-or-v1-sua-chave-aqui' > .env
```

Obtenha sua chave gratuita em: https://openrouter.ai/keys

## 4. Testar Conexão

```python
# test.py
import os, httpx, json
from dotenv import load_dotenv
load_dotenv()

resp = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    },
    json={
        "model": "google/gemini-2.5-flash-lite",
        "messages": [{"role": "user", "content": "Diga olá em uma frase!"}],
    },
    timeout=30,
)
print(resp.json()["choices"][0]["message"]["content"])
```

```bash
python test.py
# Deve imprimir algo como: "Olá! Como posso ajudar você hoje?"
```

## 5. Editor (VS Code)

Extensões recomendadas:
- **Python** (Microsoft)
- **Pylance**
- **Even Better TOML** (opcional para pyproject.toml)

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `pip: command not found` | Instale Python 3.10+ de python.org |
| `ModuleNotFoundError: langgraph` | Ative o venv: `source .venv/bin/activate` |
| `401 Unauthorized` | Verifique OPENROUTER_API_KEY no .env |
| `Timeout` | Verifique conexão com internet |

---

**Próximo:** [02-primeiro-projeto.md](./02-primeiro-projeto.md)
