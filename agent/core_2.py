from .llm_handler import LLMHandler
from .memory import MemoryManager
from .material_manager import MaterialManager, MaterialFormatter
from .rag import GuideRAG
from .scaffolding_agent import ScaffoldingAgent


class AgenticTutor:
    def __init__(self):
        self.memory = MemoryManager()
        self.llm = LLMHandler()
        self.scaffolding = ScaffoldingAgent()
        self.material_manager = MaterialManager(
            memory_manager=self.memory, 
            formatter=MaterialFormatter()
        )
        self.rag = None

    
    def interpret_student_message(self, last_question, user_message):
        if not last_question:
            return "NOVO_TOPICO", "NAO_AVALIAVEL", None

        prompt = f"""
        Você é um agente responsável por interpretar mensagens
        de estudantes em uma plataforma de aprendizagem de inglês.

        Analise a última intervenção do tutor, identificando
        a pergunta ou atividade que o aluno deveria responder.

        ÚLTIMA INTERVENÇÃO DO TUTOR:
        {last_question}

        MENSAGEM DO ALUNO:
        {user_message}

        Identifique:

        1. INTENÇÃO:
        - CONTINUAR: responde ou interage com a atividade atual.
        - NOVO_TOPICO: inicia outro assunto ou solicita outra atividade.

        2. AVALIAÇÃO:
        - CORRETA: resposta adequada ao exercício.
        - INCORRETA: resposta apresenta erro relevante.
        - NAO_AVALIAVEL: não é possível avaliar ou o aluno não respondeu.

        3. INSTRUÇÃO:
        Uma orientação breve para o tutor principal.

        IMPORTANTE:
        - Não considere uma dúvida como resposta incorreta.
        - Não considere uma solicitação de explicação como erro.
        - Avalie a resposta considerando o contexto do exercício.
        - Não confunda uma resposta parcialmente correta com
        uma resposta completamente incorreta.

        Responda EXCLUSIVAMENTE neste formato:

        INTENÇÃO | AVALIAÇÃO | INSTRUÇÃO
        """

        result = self.llm.generate_internal(
            system_prompt=(
                "Você é um agente interno de classificação "
                "pedagógica. Não converse com o estudante. "
                "Siga rigorosamente o formato solicitado. "
                "Escreva a orientação em português brasileiro."
            ),
            user_message=prompt
        )

        try:
            action, evaluation, instruction = result.split("|", 2)

            return (
                action.strip().upper(),
                evaluation.strip().upper(),
                instruction.strip()
            )

        except ValueError:
            return "CONTINUAR", "NAO_AVALIAVEL", result.strip()

    def continue_mini_game(self, user_id):
        learning_state = self.memory.get_learning_state(user_id)
        current_category = learning_state.get("current_category", "vocabulario")

        class_info = self.memory.get_class("class_01")
        category_topics = class_info.get("topics", []) if class_info else []

        progress = self.memory.get_progress(user_id, "class_01")
        previous_topics = list(progress.keys())

        remaining_topics = [t for t in category_topics if t not in previous_topics]
        next_topic = remaining_topics[0] if remaining_topics else (category_topics[0] if category_topics else "General Practice")

        self.memory.update_learning_state(user_id, last_topic=next_topic)
        return f"🎲 Let's start the mini-game on {current_category}! First activity is based on the topic '{next_topic}'."

    def respond(self, user_id, message, class_id="class_01", topics_queue=None, is_new_session=False):
        profile = self.memory.get_user_profile(user_id)
        if not profile or "level" not in profile or "module" not in profile:
            return "Before we start, I need to know your level and module. 🙂"

        # 1. Salva mensagem do usuário no histórico
        self.memory.update_history(user_id, f"Aluno: {message}")

        # 2. Identifica os tópicos selecionados no brainstorming
        duvidas = []

        if topics_queue:
            duvidas = [
                t["name"] if isinstance(t, dict) else t
                for t in topics_queue
            ]

        # Recupera o tópico que estava sendo trabalhado
        learning_state = self.memory.get_learning_state(user_id)
        last_topic = learning_state.get("last_topic")
        last_question = None if is_new_session else learning_state.get("last_question")

        # Verifica se o aluno solicitou outro tópico da fila
        topico_solicitado = next(
            (
                topico for topico in duvidas
                if topico.casefold() in message.casefold()
            ),
            None
        )

        # Define o foco da revisão
        if is_new_session:
            topicos_foco = duvidas[0] if duvidas else "Prática Geral"
        elif topico_solicitado:
            topicos_foco = topico_solicitado
        elif last_topic and any(
            last_topic.strip().casefold() == t.strip().casefold()
            for t in duvidas
        ):
            topicos_foco = next(
                t for t in duvidas
                if t.strip().casefold() == last_topic.strip().casefold()
            )
        else:
            topicos_foco = duvidas[0] if duvidas else "Prática Geral"

        # Persiste o tópico atual
        if duvidas:
            self.memory.update_learning_state(
                user_id,
                last_topic=topicos_foco
            )
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

        # 4. Lê estado, histórico e progresso no Supabase
        context = (
            ""
            if is_new_session
            else self.memory.get_context(user_id)
        )
        learning_state = self.memory.get_learning_state(user_id)
        class_progress = self.memory.get_progress(user_id, class_id)
        current_category = current_category or learning_state.get("current_category")
        
        raw_level = learning_state.get("level") or profile.get("level", "a1")
        level = str(raw_level).lower().strip()
        current_module = learning_state.get("current_module") or profile.get("module", "Vocabulary")
        last_topic = learning_state.get("last_topic") or topicos_foco

        previous_words = [w.lower() for w in (self.memory.get_taught_words(user_id) or [])]
        previous_topics = [t.lower() for t in class_progress.keys()]

        # 5. Avalia intenção do aluno via mini-agente
        action, evaluation, instruction = self.interpret_student_message(
            last_question=last_question,
            user_message=message
        )


        
        # 6. Controle do scaffolding
        topic_key = next(
            (
                topic for topic in class_progress
                if topic.strip().casefold()
                == topicos_foco.strip().casefold()
            ),
            topicos_foco
        )
        
        topic_info = class_progress.get(topic_key, {})
        attempts = int(topic_info.get("attempts") or 0)
        
        if is_new_session:
            action = "NOVO_TOPICO"
        
        elif last_question and topico_solicitado:
            if last_topic and (
                topico_solicitado.casefold()
                != last_topic.casefold()
            ):
                action = "NOVO_TOPICO"
        
        attempts_before = attempts
        reset_after_response = False
        
        if action == "NOVO_TOPICO":
        
            attempts = 0
            attempts_before = 0
        
            self.memory.update_topic_progress(
                user_id=user_id,
                class_id=class_id,
                topic=topic_key,
                status="in_progress",
                reset_attempts=True
            )
        
        elif action == "CONTINUAR":
        
            if evaluation == "INCORRETA":
        
                self.memory.update_topic_progress(
                    user_id=user_id,
                    class_id=class_id,
                    topic=topic_key,
                    status="in_progress",
                    increment_attempt=True
                )
        
                attempts += 1
        
                if self.scaffolding.determine_level(
                    attempts_before
                ) == 3:
                    reset_after_response = True
        
            elif evaluation == "CORRETA":
        
                attempts = 0
                attempts_before = 0
        
                self.memory.update_topic_progress(
                    user_id=user_id,
                    class_id=class_id,
                    topic=topic_key,
                    status="in_progress",
                    reset_attempts=True
                )
        
            elif evaluation == "NAO_AVALIAVEL":
                # Dúvidas não são contabilizadas como erros.
                pass
        
        print("\n========== DEBUG COMUM ==========")
        print("MENSAGEM:", message)
        print("AÇÃO:", action)
        print("AVALIAÇÃO:", evaluation)
        print("TÓPICO:", topicos_foco)
        print("TENTATIVAS ANTERIORES:", attempts_before)
        print(
            "NÍVEL DE SCAFFOLDING:",
            self.scaffolding.determine_level(attempts_before)
        )
        print("================================\n")


        # 7. Busca materiais de apoio (RAG / Banco)
        materials_str = f"🎯 FOCO OBRIGATÓRIO DA AULA: {topicos_foco}\n"
        if current_category:
            self.rag = GuideRAG(
                user_id=user_id,
                categoria=current_category,
                memory_manager=self.memory,
                class_id=class_id
            )
            rag_output = self.rag.query(message)
            if rag_output:
                materials_str += f"\nConteúdo RAG: {rag_output}"
            else:
                extra_materials = self.material_manager.get_materials_by_category(
                    user_id=user_id,
                    category=current_category,
                    class_id=class_id
                )
                materials_str += "\n" + "\n".join([f"- [{m['topic']}]: {m['content']}" for m in extra_materials])

        # 8. Gera a instrução do Scaffolding
        scaffolding_instruction = self.scaffolding.build_system_instruction(
            selected_topics=topicos_foco,
            attempts=attempts_before,
            student_level=level
        )

        # 9. Gera a resposta enviando o scaffolding_prompt isolado ao LLMHandler
        response_text, new_word = self.llm.generate(
            context=context,
            message=f"""
            TÓPICO PEDAGÓGICO ATUAL:
            {topicos_foco}
        
            MENSAGEM DO ESTUDANTE:
            {message}
        
            AVALIAÇÃO DA RESPOSTA:
            {evaluation}
        
            INTENÇÃO IDENTIFICADA:
            {action}
        
            ORIENTAÇÃO DO AGENTE INTERPRETADOR:
            {instruction or "Nenhuma orientação adicional."}
        
            RESTRIÇÕES:
            - Trabalhe exclusivamente o tópico informado.
            - Não introduza outros conteúdos.
            - Respeite o nível de scaffolding recebido.
            - Utilize português brasileiro nas explicações.
            - Se a solicitação for uma revisão genérica,
              inicie uma atividade diretamente relacionada
              ao tópico informado.
            """,
            scaffolding_prompt=scaffolding_instruction,
            materials_context=materials_str,
            level=level,
            current_module=current_module,
            last_topic=topicos_foco,
            previous_words=previous_words,
            previous_topics=previous_topics,
            has_previous_sessions=bool(context)
        )

        if reset_after_response and response_text:
            if not response_text.startswith(
                "Ocorreu um erro ao processar"
            ):
                self.memory.update_topic_progress(
                    user_id=user_id,
                    class_id=class_id,
                    topic=topic_key,
                    status="in_progress",
                    reset_attempts=True
                )

        # 10. Atualiza o histórico no banco de dados
        self.memory.update_history(user_id, f"Tutor: {response_text}", role="tutor")

        # 11. Salva a última intervenção do tutor para a próxima interação
        self.memory.update_learning_state(user_id, last_question=response_text)

        if new_word:
            if new_word.lower() not in previous_words:
                self.memory.add_taught_word(user_id, new_word)
            self.memory.update_topic_progress(user_id, class_id, new_word.lower(), "presented")

        if current_category:
            try:
                self.material_manager.add_material(
                    user_id=user_id, 
                    category=current_category, 
                    raw_text=response_text
                )
            except Exception as e:
                print("Erro ao salvar material no Supabase:", e)

        return response_text
