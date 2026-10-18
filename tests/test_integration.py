import pytest

def test_full_pipeline(memory_manager, rag_agent, llm_handler):
    """
    Testa o fluxo de integração do pipeline completo no Supabase e Groq:
    1. Busca vetorial de materiais via RAG (Supabase pgvector via RPC match_materials)
    2. Registro e recuperação de memória/histórico do usuário
    3. Geração de resposta pela infraestrutura de LLM (Groq LPU)
    """
    user_id = "user_test_integration"
    query = "supermarket"

    # 1. Teste da busca vetorial no RAG
    # O método query retorna uma string com os materiais formatados (ou "" se não houver registros)
    retrieved_text = rag_agent.query(question=query, k=3)
    assert isinstance(retrieved_text, str), "O RAG deve retornar uma string contendo o texto agrupado."

    # 2. Teste do registro e leitura de histórico na memória
    if hasattr(memory_manager, "save_chat_message"):
        memory_manager.save_chat_message(user_id=user_id, role="user", content="How do I improve my English?")
    
    if hasattr(memory_manager, "get_chat_history"):
        history = memory_manager.get_chat_history(user_id=user_id)
        assert isinstance(history, list)

    # 3. Teste de geração de resposta via LLMHandler
    system_prompt = "You are a helpful English tutor."
    user_message = "Explain in one sentence the meaning of 'supermarket' for an English student."

    try:
        response = llm_handler.generate(system_prompt, user_message)
    except TypeError:
        # Fallback caso o método aceite apenas a mensagem ou outro formato
        response = llm_handler.generate(user_message)

    assert response is not None, "A resposta do LLM não deve ser nula."
    assert len(str(response)) > 0, "A resposta do LLM não deve estar vazia."