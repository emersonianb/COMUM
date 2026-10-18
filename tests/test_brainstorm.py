import os
import pytest
from agent.content_agent import ContentAgent
from agent.memory import MemoryManager

def test_brainstorm_pull():
    # 1. Inicializa a memória e o agente de conteúdo
    memory_manager = MemoryManager()
    agent = ContentAgent(memory=memory_manager)

    user_id = "usuario_teste"
    teacher_id = "prof_01"

    # 2. Executa a construção do roadmap de brainstorm
    roadmap = agent.build_brainstorm_roadmap(user_id=user_id, teacher_id=teacher_id)

    # 3. Exibição para inspeção visual no terminal (pytest -s)
    print("\n" + "=" * 45)
    print(" 🎯 TÓPICOS PUXADOS PARA O BRAINSTORM")
    print("=" * 45)
    print(f"📌 Aula ID: {roadmap.get('class_id')} | Título: {roadmap.get('title')}\n")
    
    topics = roadmap.get("topics", [])
    
    if not topics:
        print("ℹ️ Nenhum tópico retornado para esta aula ou usuário.")
    else:
        print("Palavras/Tópicos extraídos:")
        for index, item in enumerate(topics, 1):
            if isinstance(item, dict):
                topic_name = item.get("topic") or item.get("name") or "Sem nome"
                status = item.get("status", "desconhecido")
            else:
                topic_name = str(item)
                status = "não informado"
            print(f"   {index}. Tópico: '{topic_name}' (Status: {status})")
            
    print("=" * 45)

    # 4. Asserções formais para o Pytest
    assert isinstance(roadmap, dict), "O roadmap retornado deve ser um dicionário."
    assert "class_id" in roadmap, "O roadmap deve conter a chave 'class_id'."
    assert "title" in roadmap, "O roadmap deve conter a chave 'title'."
    assert "topics" in roadmap, "O roadmap deve conter a chave 'topics'."
    assert isinstance(roadmap["topics"], list), "A chave 'topics' deve ser uma lista."

if __name__ == "__main__":
    test_brainstorm_pull()