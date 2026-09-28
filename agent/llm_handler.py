import os
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

class LLMHandler:
    def __init__(self, model="openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            model=model,
            temperature=0.4,
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.system_prompt = """
        Você é um tutor de inglês motivador e amigável, falando principalmente em Português.

        --- Escopo e Limitações Strict (MUITO IMPORTANTE) ---
        1. **Tradução/Dúvida de Inglês Fora do Tópico:** Se o aluno perguntar como se diz algo em inglês ou pedir uma tradução pontual (mesmo fora do tópico atual), responda de forma ultra direta (1 frase) e VOLTE IMEDIATAMENTE para o exercício/tópico da aula na linha seguinte.
        2. **Assuntos Alheios ao Inglês:** Se o aluno perguntar sobre política, história, opiniões pessoais ou assuntos gerais, recuse educadamente de forma breve e reconduza-o para a aula.
        3. **Engajamento Contínuo (OBRIGATÓRIO):** TODA mensagem sua DEVE terminar com uma pergunta prática, um desafio ou um chamado para o aluno responder. NUNCA encerre com frases passivas como "estou à disposição" ou "se quiser é só me dizer".
        
        --- Regras de Comportamento ---
        - Fale de forma clara, amigável e motivadora.
        - Use emojis apenas para reforçar emoção.
        - **Nunca repita tópicos ou palavras já ensinadas.**
        - Ensine apenas um novo item por vez.
        - Todo novo termo deve conter:
            1. Palavra/expressão em inglês
            2. Tradução
            3. Pronúncia simplificada (Português)
        - Faça apenas uma pergunta de cada vez.
        - Se o aluno respondeu à última pergunta → continue o mesmo tópico.
        - Se o aluno pediu um método diferente → inicie mini-jogo imediatamente.
        - Não inclua saudações automáticas repetidas.
        - Siga SEMPRE a instrução do mini agente.
        - **IMPORTANTE:** Toda vez que ensinar uma palavra ou tópico novo em inglês, inclua obrigatoriamente no final da mensagem a tag: NEW_TOPIC: <palavra_em_ingles>

        --- Instruções do mini-agente ---
        {instruction}

        --- Dados do Aluno e Aula ---
        Level: {level}
        Module: {current_module}
        Last topic: {last_topic}
        Previously taught topics: {previous_topics}
        Previously taught vocabulary: {previous_words}
        Has previous sessions: {has_previous_sessions}

        --- Materiais de Apoio (SQLite) ---
        {materials_context}
        """

    def generate(self, context, message,
                 materials_context="",
                 level="A1",
                 current_module="Vocabulary",
                 last_topic="none",
                 previous_topics=None,
                 previous_words=None,
                 has_previous_sessions=False,
                 instruction=""):
        try:
            previous_topics = previous_topics or []
            previous_words = previous_words or []

            previous_topics_str = ", ".join(previous_topics) if previous_topics else "none"
            previous_words_str = ", ".join(previous_words) if previous_words else "none"

            system_prompt_filled = self.system_prompt.format(
                level=level,
                current_module=current_module,
                last_topic=last_topic,
                previous_topics=previous_topics_str,
                previous_words=previous_words_str,
                has_previous_sessions=has_previous_sessions,
                instruction=instruction,
                materials_context=materials_context or "Nenhum material extra cadastrado."
            )

            # Recompõe o histórico formatando adequadamente as mensagens do banco
            dialogue_history = ""
            if isinstance(context, list):
                for entry in context:
                    dialogue_history += f"{entry.get('message', '')}\n"
            elif isinstance(context, str):
                dialogue_history = context

            # Evita duplicar a última mensagem caso ela já tenha entrado via histórico
            if message and not dialogue_history.strip().endswith(message.strip()):
                dialogue_history += f"Aluno: {message}\n"

            messages = [
                SystemMessage(content=system_prompt_filled),
                HumanMessage(content=dialogue_history)
            ]

            response = self.llm.invoke(messages)

            # Extrai a tag NEW_TOPIC informada pelo modelo
            match_word = re.search(r'NEW_TOPIC:\s*([A-Za-z\s]+)', response.content)
            new_word = match_word.group(1).strip() if match_word else None

            # Remove a tag interna antes de exibir o texto ao aluno
            user_facing_response = re.sub(r'NEW_TOPIC:\s*[A-Za-z\s]+', '', response.content).strip()
            if new_word and "?" not in user_facing_response:
                user_facing_response += f"\n\nCan you try using '{new_word}' in a sentence?"

            return user_facing_response, new_word

        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return "Sorry, there was an error processing your message. Please try again.", None