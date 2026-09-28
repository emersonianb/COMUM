# agent/scaffolding_agent.py

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

    def build_system_instruction(self, topic: str, attempts: int, context: str = "") -> str:
        """
        Gera a instrução restritiva (Guardrail) que será injetada no Prompt da API.
        """
        level = self.determine_level(attempts)
        instruction = self.scaffolding_levels[level]

        system_prompt = f"""
Você é o Tutor de Inglês da plataforma COMUM. Seu objetivo é ajudar o aluno usando Scaffolding Pedagógico.

Tópico Atual: {topic}
Contexto do Conteúdo: {context if context else 'Geral'}
Nível Atual de Andaime: Nível {level}

REGRA PEDAGÓGICA OBRIGATÓRIA:
{instruction}

Diretrizes adicionais:
- Responda em Português quando for explicar conceitos, mas mantenha termos ou frases em Inglês para prática.
- Mantenha respostas curtas e acolhedoras (no máximo 3 a 4 frases).
- NUNCA dê a resposta pronta se o nível for 1 ou 2.
"""
        return system_prompt