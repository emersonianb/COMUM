import os
import json
from groq import Groq

class ContentAgent:
    """
    Responsável por:
    - Conhecer o conteúdo disponibilizado pelos professores (armazenado no Supabase).
    - Cruzar com o progresso do aluno para saber o que foi dominado, parcial ou esquecido.
    - Gerar a lista de tópicos para o brainstorm inicial.
    - Atuar como "guia" para o agente principal para evitar repetição de conteúdo.
    """

    def __init__(self, memory=None):
        self.memory = memory
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = None

    def get_current_class(self, user_id, teacher_id="prof_01"):
        """
        Busca a aula mais recente disponível no Supabase para o professor fornecido.
        """
        classes = self.memory.list_classes(teacher_id=teacher_id)
        if not classes:
            return None
        latest = classes[-1]
        class_id = latest.stem if hasattr(latest, 'stem') else str(latest)
        return class_id, self.memory.get_class(class_id, teacher_id=teacher_id)

    def build_brainstorm_roadmap(self, user_id, teacher_id="prof_01", class_id=None):
        """
        Gera a lista de tópicos que o agente de diagnóstico abordará no brainstorm,
        priorizando tópicos esquecidos ou parciais.
        """
        if class_id:
            class_data = self.memory.get_class(class_id, teacher_id=teacher_id)
            result = (class_id, class_data) if class_data else self.get_current_class(user_id, teacher_id=teacher_id)
        else:
            result = self.get_current_class(user_id, teacher_id=teacher_id)

        if not result or not result[1]:
            return {"class_id": class_id, "title": "Aula Não Encontrada", "topics": []}

        target_class_id, class_data = result
        pending = self.memory.get_pending_topics(user_id, target_class_id)

        # Prioridade: esquecidos -> parciais -> apresentados -> nunca vistos
        priority_order = {"forgotten": 0, "partial": 1, "presented": 2, "not_seen": 3}
        pending.sort(key=lambda t: priority_order.get(t.get("status", "not_seen"), 4))

        return {
            "class_id": target_class_id,
            "teacher_id": teacher_id,
            "title": class_data.get("title", "Sem Título"),
            "topics": pending
        }

    def record_diagnosis(self, user_id, class_id, topic, status, confidence=None):
        """
        Registra a avaliação do aluno sobre um tópico após o brainstorm.
        """
        self.memory.update_topic_progress(
            user_id=user_id,
            class_id=class_id,
            topic=topic,
            status=status,
            confidence=confidence
        )

    def get_main_agent_guide(self, user_id, teacher_id="prof_01"):
        """
        Retorna um resumo estruturado para o prompt do tutor, evitando repetições.
        """
        result = self.get_current_class(user_id, teacher_id=teacher_id)
        if not result:
            return "No class registered yet."

        class_id, class_data = result
        class_progress = self.memory.get_progress(user_id, class_id)

        mastered = [t for t, info in class_progress.items() if info.get("status") == "mastered"]
        presented = [t for t, info in class_progress.items() if info.get("status") == "presented"]
        pending = self.memory.get_pending_topics(user_id, class_id)

        return {
            "class_id": class_id,
            "teacher_id": teacher_id,
            "title": class_data.get("title"),
            "description": class_data.get("description"),
            "mastered_topics": mastered,
            "presented_unconfirmed_topics": presented,
            "pending_topics": [p["topic"] for p in pending]
        }

    def generate_student_flashcards(self, class_title: str, doubt_topics: list) -> dict:
        """Gera 4 a 5 flashcards de estudo inteligentes e focados nas dúvidas do aluno."""
        if not self.client:
            return {"flashcards": []}

        topics_str = ", ".join(doubt_topics) if doubt_topics else "Geral e revisão básica"

        prompt = f"""
Você é um tutor pedagógico de inglês adaptativo para alunos brasileiros. Crie de 4 a 5 flashcards focando nas DÚVIDAS do aluno.

Aula: {class_title}
Tópicos de Dificuldade do Aluno: {topics_str}

REGRAS OBRIGATÓRIAS DE IDIOMA E ESTRUTURA:
1. A DICA ("hint") DEVE ESTAR 100% EM PORTUGUÊS!
   - Exemplo: "Lembre-se de usar 'am' para a primeira pessoa."
2. SE FOR PEDIR TRADUÇÃO: O enunciado no "front" DEVE estar em PORTUGUÊS.
   - Exemplo no front: "Como se diz 'Eu não sou estudante' em inglês?"
   - Exemplo no back: "I am not a student."
3. SE FOR COMPLETAR LACUNA: Coloque a frase com lacuna (_____) no "front".
   - Exemplo no front: "Complete: I _____ not a student."
   - Exemplo no back: "am"

ESTRUTURA JSON EXIGIDA (Responda APENAS o JSON):
{{
  "flashcards": [
    {{
      "front": "Pergunta em português OU frase em inglês com lacuna (_____)",
      "back": "Resposta correta em inglês / frase completa",
      "hint": "Dica pedagógica em PORTUGUÊS sem dar a resposta inteira"
    }}
  ]
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Erro ao gerar flashcards: {e}")
            return {
                "flashcards": [
                    {
                        "front": "Como se diz 'Eu não sou estudante' em inglês?",
                        "back": "I am not a student.",
                        "hint": "Use o verbo to be na negativa para o pronome 'I'."
                    }
                ]
            }

    def generate_student_minigame(self, class_title: str, doubt_topics: list) -> dict:
        """Gera jogos variados, incluindo Missão de RPG com Avatar Interativo."""
        if not self.client:
            return {"game_type": "quiz", "game_title": "Desafio", "questions": []}

        topics_str = ", ".join(doubt_topics) if doubt_topics else "Geral"

        prompt = f"""
Você é um designer de jogos pedagógicos. Crie um mini-jogo interativo focado nas DÚVIDAS do aluno.
Aula: {class_title}
Tópicos de Dificuldade: {topics_str}

Escolha ALEATORIAMENTE um dos 4 tipos de jogo abaixo e responda EXCLUSIVAMENTE em JSON:

TIPO 1: "avatar_quest" (Missão de RPG / Diálogo com Avatar - RECOMENDADO)
{{
  "game_type": "avatar_quest",
  "game_title": "Missão de Diálogo",
  "avatar_name": "Tutor Leo",
  "avatar_icon": "👨‍🚀",
  "story": "Leo precisa da sua ajuda para pegar o voo correto no aeroporto!",
  "steps": [
    {{
      "expression": "🤔",
      "speech": "Excuse me! _____ is the check-in desk for London?",
      "options": ["Where", "What", "Who"],
      "answer_index": 0,
      "feedback": "Excelente! 'Where' é usado para perguntar 'Onde'."
    }}
  ]
}}

TIPO 2: "quiz" (Múltipla escolha)
{{
  "game_type": "quiz",
  "game_title": "Quiz do Conhecimento",
  "questions": [
    {{
      "question": "Pergunta sobre os tópicos",
      "options": ["Opção A", "Opção B", "Opção C"],
      "answer_index": 0,
      "explanation": "Explicação pedagógica"
    }}
  ]
}}

TIPO 3: "unscramble" (Organize as palavras da frase)
{{
  "game_type": "unscramble",
  "game_title": "Monte a Frase Correta",
  "items": [
    {{
      "scrambled": ["am", "I", "student", "a"],
      "correct": "I am a student",
      "translation": "Eu sou um estudante"
    }}
  ]
}}

TIPO 4: "match" (Ligue os Pares)
{{
  "game_type": "match",
  "game_title": "Ligue os Pares",
  "pairs": [
    {{"english": "Apple", "portuguese": "Maçã"}},
    {{"english": "Book", "portuguese": "Livro"}}
  ]
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Erro ao gerar mini-game: {e}")
            return {"game_type": "quiz", "game_title": "Quiz", "questions": []}