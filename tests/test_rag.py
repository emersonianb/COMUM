import pytest
from agent.rag import GuideRAG

@pytest.fixture
def user_id():
    return "user_test_rag_diverse"

@pytest.fixture
def rag_system(memory_manager, user_id):
    category = "vocabulario"
    memory_manager._ensure_user(user_id)

    rag = GuideRAG(user_id=user_id, categoria=category, memory_manager=memory_manager)
    
    mats = [
        ("I went to the restaurant to order dinner.", "Restaurante e Jantar"),
        ("She visited the library to study grammar.", "Biblioteca e Estudos"),
        ("We booked a hotel room near the beach.", "Viagem e Hotel")
    ]

    for content_text, topic_text in mats:
        vector = rag.embeddings.embed_query(content_text)
        memory_manager.supabase.table("user_materials").upsert({
            "user_id": user_id,
            "category": category,
            "topic": topic_text,
            "content": content_text,
            "embedding": vector
        }).execute()

    return rag

def test_rag_index_and_query(rag_system, user_id):
    """Testa a busca por similaridade exata da palavra-chave."""
    results = rag_system.query(question="restaurant", k=1)
    assert isinstance(results, str)
    assert "restaurant" in results.lower()

def test_rag_k_neighbors_scoping(rag_system):
    """Testa a diferença de volume de contexto recuperado ajustando k=1 vs k=3."""
    res_k1 = rag_system.query(question="places to go", k=1)
    res_k3 = rag_system.query(question="places to go", k=3)

    assert len(res_k3) >= len(res_k1)

def test_rag_query_with_punctuation_and_accents(rag_system):
    """Garante que pontuações e acentuações na dúvida do aluno não quebram o vetor no Supabase."""
    results = rag_system.query(question="Onde fica o HOTEL???", k=1)
    assert isinstance(results, str)
    assert "hotel" in results.lower()

def test_rag_empty_results_for_unknown_user(memory_manager):
    """Garante isolamento de dados: usuário sem registros não recebe contexto de outros."""
    empty_rag = GuideRAG(user_id="user_totalmente_desconhecido", categoria="vocabulario", memory_manager=memory_manager)
    results = empty_rag.query(question="restaurant", k=1)
    assert results == ""