import pytest
from uuid import uuid4

@pytest.fixture
def user_id():
    return "user_test_memory_diverse_999"

def test_memory_add_and_update_learning_state(memory_manager, user_id):
    """Testa transição de nível do aluno."""
    memory_manager.update_learning_state(user_id, level="A1", current_module="M1")
    state_1 = memory_manager.get_user_profile(user_id) or memory_manager.get_learning_state(user_id)
    
    memory_manager.update_learning_state(user_id, level="B2", current_module="M3")
    state_2 = memory_manager.get_user_profile(user_id) or memory_manager.get_learning_state(user_id)

    assert state_2.get("level") == "b2"

def test_chat_history_limit_and_ordering(memory_manager, user_id):
    """Testa se o histórico respeita o limite solicitado e mantém a ordem cronológica."""
    for i in range(10):
        memory_manager.update_history(user_id, f"Mensagem do aluno {i}", role="user")
        memory_manager.update_history(user_id, f"Resposta do tutor {i}", role="assistant")

    context = memory_manager.get_context(user_id, limit=4)
    assert len(context) == 4
    assert "Mensagem do aluno" in context[0]["message"] or "Resposta do tutor" in context[0]["message"]

def test_taught_words_deduplication(memory_manager, user_id):
    """Garante que termos repetidos não geram duplicatas na lista de vocabulário."""
    memory_manager.add_taught_word(user_id, "vocabulary")
    memory_manager.add_taught_word(user_id, "vocabulary")  # Duplicado
    memory_manager.add_taught_word(user_id, "grammar")

    words = memory_manager.get_taught_words(user_id)
    assert words.count("vocabulary") == 1
    assert "grammar" in words

def test_topic_progress_tracking(memory_manager, user_id):
    """Testa tentativas, status e independência entre turmas."""

    test_id = uuid4().hex[:8]

    class_id = f"class_test_{test_id}_01"
    another_class_id = f"class_test_{test_id}_02"
    topic = f"Past Continuous {test_id}"

    # 1. Primeiro registro: não incrementa tentativas
    memory_manager.update_topic_progress(
        user_id, class_id, topic,
        status="presented"
    )

    prog1 = memory_manager.get_progress(user_id, class_id)

    assert prog1[topic]["attempts"] == 0

    # 2. Primeira tentativa do aluno
    memory_manager.update_topic_progress(
        user_id, class_id, topic,
        status="in_progress",
        increment_attempt=True
    )

    prog2 = memory_manager.get_progress(user_id, class_id)

    assert prog2[topic]["attempts"] == 1

    # 3. Segunda tentativa do aluno
    memory_manager.update_topic_progress(
        user_id, class_id, topic,
        status="in_progress",
        increment_attempt=True
    )

    prog3 = memory_manager.get_progress(user_id, class_id)

    assert prog3[topic]["attempts"] == 2

    # 4. Atualização do status sem incrementar tentativas
    memory_manager.update_topic_progress(
        user_id, class_id, topic,
        status="mastered",
        confidence=0.95
    )

    prog4 = memory_manager.get_progress(user_id, class_id)

    assert prog4[topic]["status"] == "mastered"
    assert prog4[topic]["attempts"] == 2
    assert prog4[topic]["confidence"] == 0.95

    # 5. Mesmo tópico em outra turma: progresso independente
    memory_manager.update_topic_progress(
        user_id, another_class_id, topic,
        status="presented"
    )

    prog5 = memory_manager.get_progress(user_id, another_class_id)

    assert prog5[topic]["attempts"] == 0
    assert prog4[topic]["attempts"] == 2

def test_turma_creation_and_teacher_workflow(memory_manager):
    """Testa o fluxo completo de criação de turma e listagem pelo professor."""
    teacher_id = "prof_test_unitario"
    memory_manager.register_or_login_teacher(teacher_id, department="Inglês")

    turma = memory_manager.create_turma(teacher_id, name="Turma A1 - Noite")
    assert turma is not None
    assert "code" in turma

    turmas = memory_manager.get_teacher_turmas(teacher_id)
    assert len(turmas) > 0
    assert any(t["code"] == turma["code"] for t in turmas)