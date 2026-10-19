# 🎓 COMUM — Agente Tutor Inteligente de Inglês

**Trabalho de Conclusão de Curso (TCC)**  
*Bacharelado em Engenharia da Computação - Instituto Federal de Ciência e Tecnologia da Paraíba*

---

### 🌟 Visão Geral

O **COMUM** é uma plataforma inteligente de tutoria para ensino de inglês como segunda língua, projetada especialmente para estudantes brasileiros. Desenvolvido inicialmente como um projeto da disciplina de Inteligência Artificial Centrada no Humando, na Universidade de Coimbra, o projeto evoluiu até chegar como TCC. O sistema integra **Inteligência Artificial Generativa**, **Scaffolding Pedagógico (Zona de Desenvolvimento Proximal - ZDP)**, **Recuperação Aumentada por Geração (RAG)** em banco vetorial e **Análise Emocional** em tempo real.

O objetivo do projeto é oferecer uma experiência adaptativa, empática e pedagogicamente fundamentada, modulando o suporte de acordo com o nível de proficiência e o histórico de tentativas do estudante.

```
       +-----------------------------------------------------------------+
       |                        PLATAFORMA COMUM                         |
       +-----------------------------------------------------------------+
                                       |
    +----------------------------------+----------------------------------+
    |                                  |                                  |
    v                                  v                                  v
[  Agente de Scaffolding  ]     [   RAG em Nuvem (pgvector)  ]     [  Groq LPU Inference  ]
   - Nível 1: Pista Socrática      - Embeddings: MiniLM-L6-v2       - Baixa Latência (<1.5s)
   - Nível 2: Explicação Guiada    - Busca Cosseno (RPC Match)      - Prompts Adaptativos
   - Nível 3: Exemplo Prático      - Isolamento por Categoria       - Modulação Emocional

```

---

## 🚀 Funcionalidades Principais

* 🧱 **Scaffolding Pedagógico Dinâmico (`ScaffoldingAgent`):** Regulação da Zona de Desenvolvimento Proximal (ZDP) de Vygotsky. O tutor evita o descarregamento cognitivo automatizado, alternando progressivamente entre dicas socráticas (Nível 1), explicações com regras (Nível 2) e modelos resolvidos (Nível 3).
* ⚡ **Inferência de Baixa Latência via Groq LPU:** Processamento de linguagem natural acelerado por unidades LPU (*Large Processing Units*), permitindo trocas de mensagens e respostas pedagógicas em menos de 1,5 segundo.
* 🔍 **RAG Ancorado no Supabase (`pgvector`):** Recuperação vetorial de materiais didáticos (gramática, vocabulário, expressões e pronúncia) por similaridade de cosseno, garantindo respostas livres de alucinações.
* 🧠 **Memória Perceptiva:** Acompanhamento de perfis de alunos, nível de proficiência (A1 a C2), turmas e vocabulário aprendido (`taught_words`).
* 💡 **Módulo de Brainstorming para Docentes:** Ferramenta para extração de tópicos e auxílio na preparação de aulas e conteúdos pedagógicos.
* 🌐 **Interface Web Moderna:** Aplicação web responsiva com comunicação via API REST/WebSockets integrada ao backend Python.

---

## 🛠️ Arquitetura e Módulos do Sistema

| Módulo / Arquivo | Responsabilidade Técnica e Pedagógica |
| :--- | :--- |
| `agent/scaffolding.py` | Mediação de andaimes pedagógicos e travas de prompt (*Guardrails* ZDP Níveis 1, 2 e 3). |
| `agent/core.py` | Orquestrador principal do fluxo do agente tutor (`AgenticTutor`). |
| `agent/llm_handler.py` | Interface de comunicação e controle de resiliência com a API Groq LPU. |
| `agent/rag.py` | Consultas por similaridade vetorial no Supabase usando RPC `match_materials`. |
| `agent/material_manager.py` | Ingestão ETL, extração de PDFs/TXTs e geração de embeddings (`all-MiniLM-L6-v2`). |
| `agent/memory_manager.py` | Persistência de perfis, controle de níveis CEFR e histórico de interações. |
| `agent/emotion_analyser.py` | Classificação de sentimento nas mensagens do estudante. |
| `app.py` / `main.py` | Servidor de API (FastAPI / Flask) responsável por servir a interface Web. |

---

## 🧪 Suíte de Testes Automatizados e Benchmark

O projeto conta com validação experimental rigorosa por meio de uma suíte de testes automatizados via `pytest`, registrando **100% de aprovação (25/25 testes aprovados)**.

```bash
pytest tests/ -s
```

## 📦 Configuração e Instalação

### 1. Clonar o Repositório

```bash
git clone https://github.com/SEU_USUARIO/agentic_tutor.git
cd agentic_tutor
```

### 2. Configurar o Ambiente Virtual Python

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Instalar dependências do backend
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto com as credenciais do sistema:

```env
GROQ_API_KEY=sua_chave_api_groq
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon_ou_service_role
```

### 4. Executar o Servidor Backend

```bash
# Exemplo com Uvicorn (FastAPI)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📋 Principais Tecnologias e Pacotes

* **Servidor API & Backend:** Python 3.12, FastAPI / Uvicorn
* **Modelos de Linguagem & LPU:** Groq LPU API, `langchain-groq`
* **Banco de Dados & Vetores:** Supabase (`pgvector`), `sentence-transformers==2.6.1`
* **Processamento de Documentos:** `PyMuPDF (fitz)`, `pandas`, `numpy`
* **Testes & Qualidade:** `pytest`

---

## 👨‍💻 Autor e Contexto Acadêmico

**Emerson Sousa**  
Trabalho de Conclusão de Curso
Bacharelado em Engenharia da Computação
**Instituto Federal de Ciência e Tecnologia da Paraíba**
