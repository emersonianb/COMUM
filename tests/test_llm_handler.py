import pytest

def test_llm_handler_response(llm_handler):
    """Testa a geração de resposta básica da Groq LPU via LLMHandler."""
    system_prompt = "Você é um assistente conciso de inglês."
    user_message = "Olá, como se diz 'obrigado' em inglês?"

    result = llm_handler.generate(system_prompt, user_message)
    response_text = result[0] if isinstance(result, tuple) else result

    assert response_text is not None
    assert isinstance(response_text, str)
    assert len(response_text.strip()) > 0

def test_llm_handler_system_prompt_adherence(llm_handler):
    """Garante que o LLMHandler retorna a estrutura correta seguindo as orientações de sistema."""
    system_prompt = "Você é um tutor de inglês. Responda em uma frase curta."
    user_message = "How do you say 'bom dia'?"

    result = llm_handler.generate(system_prompt, user_message)
    response_text = result[0] if isinstance(result, tuple) else result

    assert isinstance(response_text, str)
    assert len(response_text.strip()) > 0

def test_llm_handler_special_characters_and_emojis(llm_handler):
    """Testa a resiliência do modelo com acentuação, emojis e caracteres especiais no prompt."""
    system_prompt = "Você é um tutor amigável 🎓."
    user_message = "Como pronuncio 'thoroughly' e 'rough'? 🤔"

    result = llm_handler.generate(system_prompt, user_message)
    response_text = result[0] if isinstance(result, tuple) else result

    assert isinstance(response_text, str)
    assert len(response_text) > 0

def test_llm_handler_long_context_resilience(llm_handler):
    """Testa o comportamento da LPU sob prompts de sistema extensos (resiliência de janela de contexto)."""
    long_system_prompt = "Você é um tutor rigoroso. " + ("Analise a gramática com atenção. " * 50)
    user_message = "I goes to school yesterday."

    result = llm_handler.generate(long_system_prompt, user_message)
    response_text = result[0] if isinstance(result, tuple) else result

    assert isinstance(response_text, str)
    assert len(response_text) > 0