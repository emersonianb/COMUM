# tests/test_brainstorm.py
import json
from pathlib import Path
from agent.content_agent import ContentAgent

def test_brainstorm_pull():

    # 3. Chama o Agente de Conteúdo
    agent = ContentAgent()
    roadmap = agent.build_brainstorm_roadmap(user_id="usuario_teste", teacher_id="prof_01")

    # 4. Printa o resultado no terminal
    print("=" * 45)
    print(" 🎯 TÓPICOS PUXADOS PARA O BRAINSTORM")
    print("=" * 45)
    print(f"📌 Aula Encontrada: {roadmap.get('class_id')} | {roadmap.get('title')}\n")
    
    topics = roadmap.get("topics", [])
    
    if not topics:
        print("❌ Nenhum tópico foi encontrado no arquivo de aula.")
    else:
        print("Palavras/Tópicos extraídos:")
        for index, item in enumerate(topics, 1):
            print(f"   {index}. Tópico: '{item['topic']}' (Status do Aluno: {item['status']})")
            
    print("=" * 45)

if __name__ == "__main__":
    test_brainstorm_pull()