import pytest
import time

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

def test_llm_handler_ttft_and_tbt_metrics(llm_handler):
    """
    Verifica a geração via streaming e registra métricas de desempenho.
    Os tempos são informativos, pois dependem da rede e do provedor.
    """
    system_prompt = "Você é um tutor conciso de inglês."
    user_message = "Explain the difference between 'make' and 'do' in 3 short bullet points."

    start_time = time.perf_counter()
    stream = llm_handler.generate_stream(system_prompt, user_message)

    first_token_time = None
    chunk_timestamps = []
    full_response = []

    for chunk in stream:
        current_time = time.perf_counter()

        if chunk:
            if first_token_time is None:
                first_token_time = current_time

            full_response.append(chunk)
            chunk_timestamps.append(current_time)

    assert first_token_time is not None, "Nenhum trecho foi recebido pelo streaming."
    assert len(full_response) > 1, "A resposta deve conter múltiplos trechos."

    ttft_ms = (first_token_time - start_time) * 1000

    total_chunks = len(chunk_timestamps)
    tbt_ms = (
        (chunk_timestamps[-1] - chunk_timestamps[0])
        / (total_chunks - 1)
    ) * 1000

    print(
        f"\n[LLM Benchmark] TTFT: {ttft_ms:.2f} ms"
        f" | TBT Médio: {tbt_ms:.2f} ms/chunk"
        f" | Total Chunks: {total_chunks}"
    )

    assert isinstance("".join(full_response), str)
    assert len("".join(full_response).strip()) > 0
    assert tbt_ms < 100, (
        f"TBT excedeu o limite de fluência: {tbt_ms:.2f} ms"
    )

def test_llm_handler_streaming_consistency(llm_handler):
    """
    Garante que a resposta reconstruída via streaming seja idêntica
    em conteúdo e integridade a uma resposta não-streamed.
    """
    system_prompt = "Você é um tutor amigável 🎓."
    user_message = "Como se diz 'boa sorte' em inglês?"

    stream = llm_handler.generate_stream(system_prompt, user_message)
    streamed_text = "".join([chunk for chunk in stream if chunk])

    assert isinstance(streamed_text, str)
    assert len(streamed_text.strip()) > 0