# migrate.py
import json
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from agent.memory import MemoryManager
from agent.models import TeacherClass, TeacherTopic


def seed_teachers(memory):
    """Lê os arquivos classes.json das pastas de professores em data/teachers/ e salva no SQLite."""
    teachers_dir = Path("data/teachers")
    if not teachers_dir.exists():
        print("⚠️ Pasta 'data/teachers' não encontrada. Pulando conteúdo dos professores.")
        return

    Session = sessionmaker(bind=memory.engine)
    with Session() as session:
        # Varre cada pasta dentro de data/teachers/ (ex: prof_01, default)
        for teacher_folder in teachers_dir.iterdir():
            if not teacher_folder.is_dir():
                continue

            teacher_id = teacher_folder.name
            classes_file = teacher_folder / "classes.json"

            if not classes_file.exists():
                continue

            print(f"Importando aulas do professor '{teacher_id}'...")
            try:
                data = json.loads(classes_file.read_text(encoding="utf-8"))
                classes_list = data.get("classes", [])

                for item in classes_list:
                    class_id = item.get("class_id")
                    if not class_id:
                        continue

                    # Evita duplicar registros se a aula já existir
                    existing = session.query(TeacherClass).filter_by(id=class_id, teacher_id=teacher_id).first()
                    if not existing:
                        nova_aula = TeacherClass(
                            id=class_id,
                            teacher_id=teacher_id,
                            title=item.get("title", f"Aula {class_id}"),
                            description=item.get("description", "")
                        )
                        session.add(nova_aula)

                        # Insere os tópicos/conceitos da aula
                        for topic_name in item.get("topics", []):
                            session.add(TeacherTopic(class_id=class_id, name=topic_name))

                session.commit()
                print(f"  └─ Aulas do '{teacher_id}' salvas no banco!")
            except Exception as e:
                print(f"  └─ Erro ao importar {teacher_id}: {e}")


def migrate_users(memory):
    """Importa os dados do arquivo data/memory.json (caso exista)."""
    json_path = Path("data/memory.json")
    if not json_path.exists():
        print("ℹ️ Arquivo 'data/memory.json' não encontrado. Iniciando sem usuários legados.")
        return

    print("Importando histórico e progresso dos usuários antigos...")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    for user_id, user_data in data.items():
        profile = user_data.get("profile", {})
        if profile:
            memory.set_user_profile(user_id, profile.get("level"), profile.get("module"))

        for h in user_data.get("history", []):
            memory.update_history(user_id, h.get("message"))

        for w in user_data.get("taught_words", []):
            memory.add_taught_word(user_id, w)

        for t in user_data.get("taught_topics", []):
            memory.add_taught_topic(user_id, t)

        ls = user_data.get("learning_state", {})
        if ls:
            memory.update_learning_state(user_id, **ls)

        for class_id, topics in user_data.get("progress", {}).items():
            for topic, details in topics.items():
                memory.update_topic_progress(
                    user_id=user_id,
                    class_id=class_id,
                    topic=topic,
                    status=details.get("status"),
                    confidence=details.get("confidence")
                )
    print("  └─ Usuários antigos importados com sucesso!")


def run():
    print("🚀 Iniciando migração e inicialização do banco SQLite...")
    memory = MemoryManager()

    # 1. Popula as tabelas do professor (teacher_classes e teacher_topics)
    seed_teachers(memory)

    # 2. Popula os dados dos usuários antigos (se houver)
    migrate_users(memory)

    print("\n✅ Processo concluído! O banco 'data/memory.db' está atualizado e pronto.")


if __name__ == "__main__":
    run()