import pytest
from agent.scaffolding_agent import ScaffoldingAgent

@pytest.fixture
def scaffolding_agent():
    return ScaffoldingAgent()

def test_determine_scaffolding_level(scaffolding_agent):
    """Testa a lógica de transição automática entre os 3 níveis de andaime pedagógico."""
    assert scaffolding_agent.determine_level(0) == 1, "0 tentativas deve retornar Nível 1 (Pista/Socrático)"
    assert scaffolding_agent.determine_level(-1) == 1, "Tentativas negativas devem retornar Nível 1 por segurança"
    assert scaffolding_agent.determine_level(1) == 2, "1 tentativa deve progredir para Nível 2 (Explicação Guiada)"
    assert scaffolding_agent.determine_level(2) == 3, "2 tentativas devem progredir para Nível 3 (Exemplo Prático)"
    assert scaffolding_agent.determine_level(5) == 3, "Tentativas adicionais devem manter o Nível 3"

    print("\n" + "="*60)
    print("🔹 TESTE 1: Lógica de Transição de Níveis de Scaffolding")
    print("="*60)
    print("✅ Nível 1 (Pista/Socrático)  : 0 tentativas")
    print("✅ Nível 2 (Explicação Guiada): 1 tentativa")
    print("✅ Nível 3 (Exemplo Prático)  : >= 2 tentativas")
    print("="*60)

def test_build_system_instruction_prompt_guardrails(scaffolding_agent):
    """Garante que as instruções do prompt alteram-se corretamente de acordo com o nível."""
    topic = "Present Continuous"
    context = "O aluno está tentando formar frases com to be + -ing."

    # Nível 1
    prompt_lvl1 = scaffolding_agent.build_system_instruction(topic, attempts=0, context=context)
    assert "Nível Atual de Andaime: Nível 1" in prompt_lvl1
    assert "PISTA/SOCRÁTICO" in prompt_lvl1
    assert topic in prompt_lvl1

    # Nível 2
    prompt_lvl2 = scaffolding_agent.build_system_instruction(topic, attempts=1, context=context)
    assert "Nível Atual de Andaime: Nível 2" in prompt_lvl2
    assert "EXPLICAÇÃO GUIADA" in prompt_lvl2

    # Nível 3
    prompt_lvl3 = scaffolding_agent.build_system_instruction(topic, attempts=2, context=context)
    assert "Nível Atual de Andaime: Nível 3" in prompt_lvl3
    assert "EXEMPLO PRÁTICO" in prompt_lvl3

    print("\n" + "="*60)
    print("🔹 TESTE 2: Construção Dinâmica de Prompts Restritivos (Guardrails)")
    print("="*60)
    print(f"📝 Prompt Gerado (Nível 1):\n{prompt_lvl1[:220]}...")
    print("="*60)

def test_scaffolding_llm_generation(scaffolding_agent, llm_handler):
    """Testa a geração de resposta com o Guardrail de Scaffolding ativo via Groq LPU."""
    topic = "Simple Past vs Present Perfect"
    user_message = "Eu escrevi 'I have seen that movie yesterday'. Está certo?"
    
    # Injeta instrução do Nível 1 (Socrático - Não dar a resposta pronta)
    sys_prompt = scaffolding_agent.build_system_instruction(topic, attempts=0)
    result = llm_handler.generate(sys_prompt, user_message)
    response_text = result[0] if isinstance(result, tuple) else result

    print("\n" + "="*60)
    print("🔹 TESTE 3: Execução de Andaime Pedagógico na Groq LPU")
    print("="*60)
    print(f"💬 Pergunta do Aluno : {user_message}")
    print("-" * 60)
    print(f"🤖 Resposta do Tutor (Nível 1):\n{response_text}")
    print("="*60)

    assert isinstance(response_text, str)
    assert len(response_text.strip()) > 0