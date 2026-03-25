# 💚 PicPay Negócios — Bot de Suporte

Bot especialista nos procedimentos internos do Portal PicPay para Lojistas, com streaming de respostas, arquitetura orientada a objetos, interface rica e exportação de sessão.

---

## 📌 Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Arquitetura | Classe `PicPayBot` com responsabilidades bem definidas |
| Resposta | Streaming token a token |
| Interface | `rich`: painéis coloridos, tabelas e spinner |
| Validação de entrada | Tratamento de campo vazio, limite de caracteres e `strip` |
| Erros de API | Retry automático (3x) com exponential back-off |
| Histórico | Exportação da sessão em `.txt` com timestamps |
| UX | Prompt dinâmico com contador de perguntas restantes |

---

## 🗂️ Arquivos


```
.
├── picpay_bot_v2.py      # Script Python standalone
├── picpay_bot_v2.ipynb   # Notebook Jupyter interativo
└── README.md
```


---

## 🚀 Como reproduzir

### Pré-requisitos

- Python 3.10+
- Chave Gemini gratuita em https://aistudio.google.com

### 1. Clone e instale

```bash
git clone https://github.com/SEU_USUARIO/picpay-negocios-bot.git
cd picpay-negocios-bot
pip install google-genai rich
```

### 2. Configure a chave

```bash
export GEMINI_API_KEY="sua_chave_aqui"   # Linux/macOS
$env:GEMINI_API_KEY="sua_chave_aqui"     # Windows PowerShell
```

### 3. Execute

```bash
# Terminal
python picpay_bot.py

# Jupyter
jupyter notebook picpay_bot.ipynb
```

### 4. Perguntas sugeridas para o vídeo

| # | Pergunta |
|---|---|
| 1 | `Como cancelo um pedido já aceito?` |
| 2 | `Recebi um chargeback, o que faço?` |
| 3 | `Como ativo a antecipação automática?` |

Após a 3ª resposta: resumo automático gerado → tabela da sessão exibida → arquivo `.txt` salvo.

---

## 🧩 Arquitetura da classe `PicPayBot`

```
PicPayBot
├── __init__()            → inicializa client, histórico e timestamp
├── validate(text)        → sanitiza entrada (estático)
├── _prepare_message()    → injeta instrução oculta na 3ª pergunta
├── _stream_response()    → API com streaming + retry + back-off
├── ask(user_input)       → orquestra o fluxo completo
├── export_session()      → salva transcrição em .txt
└── print_session_table() → exibe tabela ao encerrar
```

---

## 📄 Licença

MIT
