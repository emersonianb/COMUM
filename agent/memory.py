import os
from pathlib import Path
from supabase import create_client, Client

class MemoryManager:
    def __init__(self, teachers_folder="data/teachers"):
        # O parâmetro teachers_folder é mantido para compatibilidade de inicialização
        self.teachers_folder = Path(teachers_folder)
        
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY não foram encontrados nas variáveis de ambiente.")
            
        self.supabase: Client = create_client(url, key)

    def _ensure_user(self, user_id: str):
        """Garante que o usuário existe na tabela 'users'."""
        res = self.supabase.table("users").select("id").eq("id", user_id).execute()
        if not res.data:
            self.supabase.table("users").insert({
                "id": user_id,
                "level": "beginner",
                "taught_words": []
            }).execute()

    def update_history(self, user_id: str, message: str, role: str = "user"):
        """Adiciona uma mensagem ao histórico do usuário."""
        self._ensure_user(user_id)
        self.supabase.table("histories").insert({
            "user_id": user_id,
            "role": role,
            "message": message
        }).execute()

    def get_context(self, user_id: str, limit: int = 5):
        """Recupera as últimas mensagens trocadas."""
        res = (
            self.supabase.table("histories")
            .select("timestamp, message, role")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        data = res.data or []
        data.reverse()
        return [{"timestamp": r.get("timestamp"), "message": r.get("message"), "role": r.get("role")} for r in data]

    def set_user_profile(self, user_id: str, level: str, module: str):
        self._ensure_user(user_id)
        self.supabase.table("users").update({"level": level, "current_module": module}).eq("id", user_id).execute()

    def get_user_profile(self, user_id: str):
        res = self.supabase.table("users").select("*").eq("id", user_id).execute()
        if not res.data:
            return {}
        u = res.data[0]
        return {
            "level": u.get("level"),
            "module": u.get("current_module"),
            "created_at": u.get("created_at")
        }

    def get_learning_state(self, user_id: str):
        res = self.supabase.table("users").select("level, current_module, last_topic, current_category, updated_at").eq("id", user_id).execute()
        if not res.data:
            return {}
        return res.data[0]

    def update_learning_state(self, user_id: str, level=None, current_module=None, last_topic=None, current_category=None, **kwargs):
        self._ensure_user(user_id)
        payload = {}
        if level is not None: payload["level"] = level
        if current_module is not None: payload["current_module"] = current_module
        if last_topic is not None: payload["last_topic"] = last_topic
        if current_category is not None: payload["current_category"] = current_category
        payload["updated_at"] = "now()"

        if payload:
            self.supabase.table("users").update(payload).eq("id", user_id).execute()

    def add_taught_word(self, user_id: str, word: str):
        """Adiciona uma palavra ao array 'taught_words' na tabela 'users'."""
        self._ensure_user(user_id)
        res = self.supabase.table("users").select("taught_words").eq("id", user_id).execute()
        words = (res.data[0].get("taught_words") or []) if res.data else []
        
        clean_word = word.lower().strip()
        if clean_word not in words:
            words.append(clean_word)
            self.supabase.table("users").update({"taught_words": words}).eq("id", user_id).execute()

    def get_taught_words(self, user_id: str):
        res = self.supabase.table("users").select("taught_words").eq("id", user_id).execute()
        if res.data and res.data[0].get("taught_words"):
            return res.data[0]["taught_words"]
        return []

    def list_classes(self, teacher_id="prof_01"):
        res = self.supabase.table("teacher_classes").select("id").eq("teacher_id", teacher_id).execute()
        # Retorna como Path para manter compatibilidade com o .stem no código do agente
        return [Path(c["id"]) for c in (res.data or [])]

    def get_class(self, class_id: str, teacher_id="prof_01"):
        res_class = self.supabase.table("teacher_classes").select("*").eq("id", class_id).eq("teacher_id", teacher_id).execute()
        if not res_class.data:
            return None
        
        t_class = res_class.data[0]
        res_topics = self.supabase.table("teacher_topics").select("name").eq("class_id", class_id).execute()
        
        return {
            "class_id": t_class["id"],
            "title": t_class.get("title"),
            "description": t_class.get("description"),
            "topics": [t["name"] for t in (res_topics.data or [])]
        }

    def get_progress(self, user_id: str, class_id: str = None):
        query = self.supabase.table("topic_progress").select("*").eq("user_id", user_id)
        if class_id:
            query = query.eq("class_id", class_id)
        
        res = query.execute()
        data = res.data or []

        progress = {}
        for r in data:
            c_id = r.get("class_id", "default")
            progress.setdefault(c_id, {})[r["topic"]] = {
                "status": r.get("status"),
                "last_review": r.get("last_review"),
                "attempts": r.get("attempts"),
                "confidence": r.get("confidence")
            }
        return progress.get(class_id, {}) if class_id else progress

    def update_topic_progress(self, user_id: str, class_id: str, topic: str, status: str, confidence: float = None):
        self._ensure_user(user_id)
        
        # Verifica se o tópico já tem histórico de tentativas
        existing = (
            self.supabase.table("topic_progress")
            .select("attempts")
            .eq("user_id", user_id)
            .eq("topic", topic)
            .execute()
        )
        
        attempts = (existing.data[0]["attempts"] + 1) if existing.data else 1

        payload = {
            "user_id": user_id,
            "class_id": class_id,
            "topic": topic,
            "status": status,
            "attempts": attempts,
            "last_review": "now()"
        }
        if confidence is not None:
            payload["confidence"] = confidence

        self.supabase.table("topic_progress").upsert(payload, on_conflict="user_id, topic").execute()

    def get_pending_topics(self, user_id: str, class_id: str):
        class_data = self.get_class(class_id)
        if not class_data:
            return []
        class_progress = self.get_progress(user_id, class_id)
        return [
            {"topic": t, "status": class_progress.get(t, {}).get("status", "not_seen")}
            for t in class_data.get("topics", [])
            if class_progress.get(t, {}).get("status") != "mastered"
        ]

    def _mark_topic_presented(self, user_id: str, class_id: str, topic: str):
        class_data = self.get_class(class_id)
        if not class_data:
            return
        class_progress = self.get_progress(user_id, class_id)
        for official in class_data.get("topics", []):
            if topic.lower() in official.lower() or official.lower() in topic.lower():
                if official not in class_progress:
                    self.update_topic_progress(user_id, class_id, official, "presented")
                break