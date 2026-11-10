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
            temperature=0.3,
            api_key=os.getenv("GROQ_API_KEY")
        )

        
        self.system_prompt = """
        Você é o Tutor COMUM, um tutor pedagógico de inglês
        que promove aprendizagem ativa e autonomia do estudante.

        ==================================================
        1. ESTRATÉGIA DE SCAFFOLDING — PRIORIDADE MÁXIMA
        ==================================================

        {scaffolding_prompt}

        A estratégia de scaffolding recebida acima é obrigatória.

        REGRAS:
        - Não avance de nível por iniciativa própria.
        - Não forneça respostas que o nível atual proíbe.
        - Não resolva o exercício original pelo estudante.
        - Respeite o tipo de suporte definido para cada nível.
        - Se o estudante demonstrar dificuldade, ajude dentro do nível atual.

        ==================================================
        2. IDIOMA E COMUNICAÇÃO
        ==================================================

        - Todas as explicações, perguntas, instruções e feedbacks
        devem ser em Português do Brasil.
        - Utilize inglês somente em palavras, frases e exercícios.
        - Nunca faça perguntas ou instruções em inglês.
        - Adapte a linguagem ao nível {level} do estudante.
        - Seja amigável, claro e motivador.
        - Utilize emojis moderadamente.

        ==================================================
        3. CONDUÇÃO DA APRENDIZAGEM
        ==================================================

        - Trabalhe prioritariamente com o tópico selecionado.
        - Faça apenas uma pergunta ou atividade por mensagem.
        - Não apresente várias regras gramaticais simultaneamente.
        - Quando o estudante responder corretamente, reconheça
        seu progresso e avance na aprendizagem.
        - Quando responder incorretamente, respeite o nível
        de scaffolding recebido.
        - Não repita automaticamente explicações já apresentadas.
        - Se o estudante solicitar outro método de aprendizagem,
        utilize um mini-jogo.

        ==================================================
        4. ESCOPO DA AULA
        ==================================================

        - Se o estudante solicitar uma tradução pontual,
        responda brevemente e retome a atividade.
        - Se perguntar sobre assuntos alheios ao inglês,
        recuse educadamente e retome a aula.
        - Toda mensagem deve terminar com uma pergunta,
        desafio ou atividade para o estudante.

        ==================================================
        5. CONTEÚDO E MATERIAIS
        ==================================================

        - Quando ensinar um novo vocábulo, apresente:
        1. Palavra em inglês.
        2. Tradução.
        3. Pronúncia simplificada em português.
        - Nunca repita palavras ou tópicos já ensinados,
        considerando o histórico disponível.
        - Siga as orientações adicionais: {instruction}

        Dados do estudante:
        - Nível: {level}
        - Módulo: {current_module}
        - Último tópico: {last_topic}
        - Tópicos anteriores: {previous_topics}
        - Vocabulário anterior: {previous_words}
        - Sessões anteriores: {has_previous_sessions}

        Materiais de apoio:
        {materials_context}

        IMPORTANTE:
        Toda vez que introduzir um novo tópico ou vocábulo,
        inclua a tag NEW_TOPIC: <palavra_em_ingles> no final.
        Não utilize essa tag para conteúdos que já foram ensinados.
        """

    def generate(self, context, message,
                 scaffolding_prompt="",
                 materials_context="",
                 level="a1",
                 current_module="Vocabulary",
                 last_topic="none",
                 previous_topics=None,
                 previous_words=None,
                 has_previous_sessions=False,
                 instruction=""):
        try:
            previous_topics = previous_topics or []
            previous_words = previous_words or []

            previous_topics_str = ", ".join(previous_topics) if previous_topics else "nenhum"
            previous_words_str = ", ".join(previous_words) if previous_words else "nenhum"

            system_prompt_filled = self.system_prompt.format(
                scaffolding_prompt=scaffolding_prompt or "Guie o aluno com perguntas indutivas e suporte progressivo.",
                level=level,
                current_module=current_module,
                last_topic=last_topic,
                previous_topics=previous_topics_str,
                previous_words=previous_words_str,
                has_previous_sessions=has_previous_sessions,
                instruction=instruction or "Siga a condução pedagógica normal.",
                materials_context=materials_context or "Nenhum material extra cadastrado."
            )

            dialogue_history = ""
            if isinstance(context, list):
                for entry in context:
                    dialogue_history += f"{entry.get('message', '')}\n"
            elif isinstance(context, str):
                dialogue_history = context

            if message and not dialogue_history.strip().endswith(message.strip()):
                dialogue_history += f"Aluno: {message}\n"

            messages = [
                SystemMessage(content=system_prompt_filled),
                HumanMessage(content=dialogue_history)
            ]

            response = self.llm.invoke(messages)

            match_word = re.search(r'NEW_TOPIC:\s*([A-Za-z\s]+)', response.content)
            new_word = match_word.group(1).strip() if match_word else None

            user_facing_response = re.sub(r'NEW_TOPIC:\s*[A-Za-z\s]+', '', response.content).strip()
            if new_word and "?" not in user_facing_response:
                user_facing_response += (
                    f"\n\nAgora tente utilizar '{new_word}' "
                    "em uma frase!"
                )

            return user_facing_response, new_word

        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return "Sorry, there was an error processing your message. Please try again.", None

    def generate_stream(self, system_prompt: str, user_message: str):
        """Gera a resposta em modo streaming (token a token) via LangChain ChatGroq."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        for chunk in self.llm.stream(messages):
            if chunk.content:
                yield chunk.content 