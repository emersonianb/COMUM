# agent/core_2.py
from .llm_handler import LLMHandler
from .memory import MemoryManager
from .material_manager import MaterialManager, MaterialFormatter
from .rag import GuideRAG

class AgenticTutor:
    def __init__(self):
        self.memory = MemoryManager()
        self.llm = LLMHandler()
        self.material_manager = MaterialManager(
            memory_manager=self.memory, 
            formatter=MaterialFormatter()
        )
        self.rag = None

    def interpret_student_message(self, last_question, user_message):
        if not last_question:
            return "NOVO_TOPICO", None

        prompt = f"""
        Você é um mini-agente tutor. Analise a mensagem do aluno e indique ao tutor principal o que fazer.

        Pergunta do tutor: "{last_question}"
        Resposta do aluno: "{user_message}"

        Responda em uma linha no formato:
        <AÇÃO> | <INSTRUÇÃO>
        Onde <AÇÃO> é:
          - CONTINUAR: se a resposta do aluno é referente à última pergunta
          - NOVO_TOPICO: se é algo novo

        E <INSTRUÇÃO> é uma sugestão do que o tutor principal deve responder.
        Não inclua saudações.
        """

        result, _ = self.llm.generate(
            context="",
            message=prompt,
            materials_context="",
            level="A1",
            current_module="default",
            last_topic="none",
            previous_words=[],
            previous_topics=[],
            has_previous_sessions=True
        )

        if "|" in result:
            action, instruction = result.split("|", 1)
            return action.strip().upper(), instruction.strip()
        else:
            return "NOVO_TOPICO", result.strip()

    def continue_mini_game(self, user_id):
        learning_state = self.memory.get_learning_state(user_id)
        current_category = learning_state.get("current_category", "vocabulario")

        class_info = self.memory.get_class("class_01")
        category_topics = class_info.get("topics", []) if class_info else []

        previous_topics = self.memory.get_taught_topics(user_id)
        remaining_topics = [t for t in category_topics if t not in previous_topics]
        next_topic = remaining_topics[0] if remaining_topics else (category_topics[0] if category_topics else "General Practice")

        self.memory.update_learning_state(user_id, last_topic=next_topic)
        return f"🎲 Let's start the mini-game on {current_category}! First activity is based on the topic '{next_topic}'."

    def respond(self, user_id, message, class_id="class_01", topics_queue=None):
        profile = self.memory.get_user_profile(user_id)
        if not profile or "level" not in profile or "module" not in profile:
            return "Before we start, I need to know your level and module. 🙂"

        # 1. Salva mensagem no histórico do SQLite
        self.memory.update_history(user_id, f"Aluno: {message}")

        # 2. Identifica os conceitos e dúvidas marcados no Brainstorm
        duvidas = []
        if topics_queue:
            duvidas = [t["name"] if isinstance(t, dict) else t for t in topics_queue]

        # Se não vier via sessão, busca direto na tabela do banco
        if not duvidas and hasattr(self.memory, "get_user_diagnostics"):
            diag = self.memory.get_user_diagnostics(user_id, class_id) or []
            duvidas = [item["topic"] for item in diag if item.get("status") in ("partial", "duvida")]

        topicos_foco = ", ".join(duvidas) if duvidas else "Prática Geral"

        # 3. Categorização simples de mensagens
        msg_lower = message.lower()
        current_category = None
        if "vocabulario" in msg_lower or "vocabulário" in msg_lower:
            current_category = "vocabulario"
        elif "gramatica" in msg_lower or "gramática" in msg_lower:
            current_category = "gramatica"
        elif "conversacao" in msg_lower or "conversação" in msg_lower:
            current_category = "conversacao"

        if current_category:
            self.memory.update_learning_state(user_id, current_category=current_category)

        # 4. Lê estado e contexto do SQLite
        context = self.memory.get_context(user_id)
        learning_state = self.memory.get_learning_state(user_id)
        
        level = learning_state.get("level") or profile.get("level", "A1")
        current_module = learning_state.get("current_module") or profile.get("module", "Vocabulary")
        last_topic = learning_state.get("last_topic", "none")

        previous_words = [w.lower() for w in (self.memory.get_taught_words(user_id) or [])]
        previous_topics = [t.lower() for t in (self.memory.get_taught_topics(user_id) or [])]

        # 5. Avalia intenção via mini-agente
        last_question = learning_state.get("last_topic")
        action, instruction = self.interpret_student_message(
            last_question=last_question,
            user_message=message
        )

        if action != "CONTINUAR":
            self.memory.update_learning_state(user_id, last_topic=message)

        # 6. Monta os materiais de contexto com FOCO OBRIGATÓRIO nos conceitos do Andaime
        materials_str = f"🎯 FOCO OBRIGATÓRIO DA AULA (CONCEITOS SELECIONADOS PELO ALUNO): {topicos_foco}\n"
        materials_str += f"O tutor DEVE focar seus exercícios e explicações EXCLUSIVAMENTE nestes tópicos: {topicos_foco}.\n"

        if current_category:
            self.rag = GuideRAG(user_id=user_id, categoria=current_category, memory_manager=self.memory)
            rag_output = self.rag.query(message)
            if rag_output:
                materials_str += f"\nConteúdo RAG: {rag_output}"
            else:
                extra_materials = self.material_manager.get_materials_by_category(user_id, current_category)
                materials_str += "\n" + "\n".join([f"- [{m['topic']}]: {m['content']}" for m in extra_materials])

        # 7. Gera resposta com a LLM
        response_text, new_word = self.llm.generate(
            context=context,
            message=instruction or message,
            materials_context=materials_str,
            level=level,
            current_module=current_module,
            last_topic=last_topic,
            previous_words=previous_words,
            previous_topics=previous_topics,
            has_previous_sessions=len(context) > 1
        )

        # 8. Atualiza histórico no SQLite
        self.memory.update_history(user_id, f"Tutor: {response_text}")

        if new_word:
            if new_word.lower() not in previous_words:
                self.memory.add_taught_word(user_id, new_word)
            if new_word.lower() not in previous_topics:
                self.memory.add_taught_topic(user_id, new_word)
            self.memory.update_learning_state(user_id, last_topic=new_word.lower())

        if current_category:
            try:
                self.material_manager.add_material(
                    user_id=user_id, 
                    category=current_category, 
                    raw_text=response_text
                )
            except Exception as e:
                print("Erro ao salvar material no SQLite:", e)

        return response_text