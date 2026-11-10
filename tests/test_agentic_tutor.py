from unittest.mock import MagicMock
from agent.core_2 import AgenticTutor

def test_agentic_tutor_integrates_with_scaffolding():
    # Instancia sem executar os construtores reais
    tutor = AgenticTutor.__new__(AgenticTutor)

    # Simula o banco de dados
    tutor.memory = MagicMock()
    tutor.memory.get_user_profile.return_value = {
        "level": "a1",
        "module": "Grammar"
    }
    tutor.memory.get_learning_state.return_value = {
        "level": "a1",
        "current_module": "Grammar",
        "last_topic": "Present Continuous"
    }
    tutor.memory.get_context.return_value = ["histórico anterior", "outra mensagem"]
    tutor.memory.get_progress.return_value = {
        "present continuous": {
            "attempts": 1,
            "status": "in_progress"
        }
    }
    tutor.memory.get_taught_words.return_value = []

    # Simula os demais componentes
    tutor.llm = MagicMock()
    tutor.llm.generate.return_value = ("Try again! You are doing well.", None)

    tutor.scaffolding = MagicMock()
    tutor.scaffolding.build_system_instruction.return_value = (
        "MÉTODO DE SCAFFOLDING ATIVO (NÍVEL 2)"
    )

    tutor.material_manager = MagicMock()
    tutor.rag = None

    # Simula a interpretação da mensagem do aluno
    tutor.interpret_student_message = MagicMock(
        return_value=("CONTINUAR", "Ajude o aluno a tentar novamente.")
    )

    # Executa
    response = tutor.respond(
        user_id="student_01",
        message="I am studying English.",
        class_id="class_01",
        topics_queue=["Present Continuous"]
    )

    # Verificações
    assert response == "Try again! You are doing well."

    tutor.scaffolding.build_system_instruction.assert_called_once_with(
        selected_topics="Present Continuous",
        attempts=2,
        student_level="a1"
    )

    tutor.llm.generate.assert_called_once()