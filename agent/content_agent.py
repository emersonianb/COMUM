# agent/content_agent.py
from .memory import MemoryManager


class ContentAgent:
    """
    Responsible for:
    - Knowing what content the teacher has provided (classes stored in SQLite).
    - Cross-referencing it with the student's progress to know what's
      already mastered, what's partial, and what's been forgotten.
    - Generating the topic list for the initial brainstorm.
    - Acting as a "guide" for the main agent so it doesn't repeat content.
    """

    def __init__(self, memory: MemoryManager = None):
        self.memory = memory or MemoryManager()

    def get_current_class(self, user_id, teacher_id="prof_01"):
        """
        Picks the latest class available in the database for the given teacher.
        """
        classes = self.memory.list_classes(teacher_id=teacher_id)
        if not classes:
            return None
        latest = classes[-1]
        class_id = latest.stem if hasattr(latest, 'stem') else str(latest)
        return class_id, self.memory.get_class(class_id, teacher_id=teacher_id)

    def build_brainstorm_roadmap(self, user_id, teacher_id="prof_01", class_id=None):
        """
        Generates the topic list the Diagnosis Agent will ask about in the
        initial brainstorm for a specific class (if class_id is passed) or 
        the current class, prioritizing topics that are forgotten or partial.
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

        # Prioridade: esquecidos primeiro, depois parciais, depois apresentados, depois nunca vistos
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
        Called by the Diagnosis Agent after evaluating the student's answer
        about a specific topic during the brainstorm.
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
        Returns a summary ready to be injected into the LLMHandler prompt,
        avoiding repetition and indicating what to prioritize in the session.
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