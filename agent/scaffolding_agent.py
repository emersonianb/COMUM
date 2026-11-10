
class ScaffoldingAgent:
    def __init__(self):
        self.scaffolding_levels = {
            1: """
            NÍVEL 1 — PISTA SOCRÁTICA:
            - Não explique a regra gramatical diretamente.
            - Não apresente a resposta correta.
            - Não forneça a tradução completa da frase solicitada.
            - Faça uma pergunta que estimule o raciocínio do estudante.
            - Se necessário, ofereça apenas uma pista pequena.
            - Permita que o estudante tente resolver sozinho.
            """,

            2: """
            NÍVEL 2 — EXPLICAÇÃO GUIADA:
            - Explique brevemente a regra ou conceito envolvido.
            - Apresente apenas a informação necessária para ajudar.
            - Não resolva o exercício do estudante.
            - Não forneça a resposta final.
            - Após a explicação, peça que o estudante tente novamente.
            """,

            3: """
            NÍVEL 3 — EXEMPLO PRÁTICO E RESOLUÇÃO:

            - Apresente a resposta correta do exercício original.
            - Explique brevemente o raciocínio utilizado.
            - Mostre como a resposta se relaciona com o conteúdo estudado.
            - Não apresente apenas a resposta: explique o aprendizado.
            - Depois, proponha uma nova atividade para verificar
            se o estudante compreendeu o conceito.
            """
        }

    def determine_level(self, attempts: int) -> int:
        """
        Define o suporte com base na quantidade
        de tentativas incorretas anteriores.
        """
        if attempts <= 0:
            return 1
        elif attempts == 1:
            return 2
        else:
            return 3

    def build_system_instruction(
        self,
        selected_topics=None,
        student_level="iniciante",
        attempts=0,
        **kwargs
    ):
        if not selected_topics:
            topics_str = "Conceitos gerais de inglês"
        elif isinstance(selected_topics, list):
            topics_str = ", ".join(selected_topics)
        else:
            topics_str = str(selected_topics)

        current_level = self.determine_level(attempts)

        scaffolding_directive = self.scaffolding_levels[current_level]

        system_instruction = f"""
        Você é o Tutor COMUM, um tutor pedagógico interativo.

        CONTEXTO DA APRENDIZAGEM:
        - Tópicos selecionados: {topics_str}
        - Nível do estudante: {student_level}
        - Tentativas incorretas anteriores: {attempts}

        ESTRATÉGIA PEDAGÓGICA OBRIGATÓRIA:

        O nível atual de scaffolding é {current_level}.

        {scaffolding_directive}

        REGRAS DE EXECUÇÃO:
        1. Siga exclusivamente a estratégia do nível atual.
        2. Não antecipe estratégias de níveis posteriores.
        3. Não entregue a resolução do exercício original.
        4. Faça apenas uma intervenção pedagógica por mensagem.
        5. Termine solicitando uma ação do estudante.
        6. Todas as explicações e instruções devem estar em português brasileiro.
        7. Utilize inglês apenas nos exemplos e exercícios.

        IMPORTANTE:
        O objetivo é desenvolver a autonomia do estudante,
        não simplesmente fornecer respostas corretas.
        """

        return system_instruction