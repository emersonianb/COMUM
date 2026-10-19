class ScaffoldingAgent:
    def __init__(self):
        # Definição dos níveis de suporte do andaime
        self.scaffolding_levels = {
            1: "PISTA/SOCRÁTICO: Não dê a resposta direta. Faça uma pergunta instigante ou dê uma dica simples.",
            2: "EXPLICAÇÃO GUIADA: Explique brevemente a regra ou conceito envolvido e peça para o aluno tentar novamente.",
            3: "EXEMPLO PRÁTICO: Apresente um exemplo semelhante resolvido e peça para ele aplicar o mesmo raciocínio ao exercício dele."
        }

    def determine_level(self, attempts: int) -> int:
        """Define o nível do andaime de acordo com o número de tentativas/erros."""
        if attempts <= 0:
            return 1
        elif attempts == 1:
            return 2
        else:
            return 3

    def build_system_instruction(self, selected_topics=None, student_level="iniciante", **kwargs):
        # 1. Trata e define a variável topics_str ANTES de usá-la na f-string
        if not selected_topics:
            topics_str = "Conceitos gerais de inglês"
        elif isinstance(selected_topics, list):
            topics_str = ", ".join(selected_topics)
        else:
            topics_str = str(selected_topics)

        # 2. Constrói o prompt com a variável já declarada
        system_instruction = f"""
        Você é o Tutor COMUM, um tutor pedagógico interativo focado no aprendizado de idiomas.

        REGRAS DE IDIOMA E INTERAÇÃO (OBRIGATÓRIO):
        1. IDIOMA DE COMUNICAÇÃO: Responda TODAS as explicações, instruções, perguntas, feedbacks e elogios SEMPRE em Português do Brasil.
        2. USO DO INGLÊS: Use o inglês EXCLUSIVAMENTE para apresentar palavras-alvo, frases de exemplo ou quando pedir para o aluno traduzir/escrever.
        3. NUNCA faça perguntas ou dê instruções em inglês (ex: JAMAIS use "Great job! Now create your sentence...", USE SEMPRE "Muito bem! Agora crie sua frase...").
        
        CONTEXTO DA AULA:
        - Tópicos focados: {topics_str}
        - Nível do aluno: {student_level}

        MÉTODO DE SCAFFOLDING (ANDAIME):
        - Faça apenas UMA pergunta ou proponha um pequeno exercício por vez.
        - Se o aluno errar ou tiver dúvidas, forneça dicas graduais em português antes de dar a resposta.
        """
        
        return system_instruction