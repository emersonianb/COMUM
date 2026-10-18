import os
import pytest
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env) para execução dos testes
load_dotenv()

from agent.memory import MemoryManager
from agent.core_2 import AgenticTutor
from agent.content_agent import ContentAgent
from agent.llm_handler import LLMHandler
from agent.rag import GuideRAG

@pytest.fixture
def memory_manager():
    """Fixture para fornecer a instância do gerenciador de memória do Supabase."""
    return MemoryManager()

@pytest.fixture
def tutor_agent():
    """Fixture para o orquestrador principal do tutor (AgenticTutor)."""
    return AgenticTutor()

@pytest.fixture
def content_agent(memory_manager):
    """Fixture para o agente de conteúdo com a memória injetada."""
    return ContentAgent(memory=memory_manager)

@pytest.fixture
def rag_agent():
    """Fixture para o mecanismo de busca vetorial RAG."""
    return GuideRAG(user_id="test_user")

@pytest.fixture
def llm_handler():
    """Fixture para a integração com a API da Groq."""
    return LLMHandler()