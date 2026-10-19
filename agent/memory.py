import os
import random
import string
from datetime import datetime, timezone
from pathlib import Path
from supabase import create_client, Client


class MemoryManager:
    def __init__(self, teachers_folder="data/teachers"):
        self.teachers_folder = Path(teachers_folder)
        
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY não foram encontrados nas variáveis de ambiente.")
            
        self.supabase: Client = create_client(url, key)

    @staticmethod
    def _normalize_level(level: str) -> str:
        """Padroniza entradas de nível para 'a1', 'a2', 'b1', 'b2', 'c1', 'c2'."""
        if not level:
            return "a1"
        
        clean = str(level).strip().lower()
        mapa_niveis = {
            "beginner": "a1",
            "begginer": "a1",
            "iniciante": "a1",
            "elementary": "a2",
            "intermediate": "b1",
            "upper intermediate": "b2",
            "upper-intermediate": "b2",
            "advanced": "c1",
            "proficient": "c2"
        }
        return mapa_niveis.get(clean, clean)

    @staticmethod
    def _parse_topics(topics) -> list:
        """
        Converte strings com ';' ou listas em uma lista limpa de tópicos em Python.
        Garante compatibilidade com colunas do tipo text[] no Supabase/PostgreSQL.
        """
        if isinstance(topics, str):
            return [t.strip() for t in topics.split(";") if t.strip()]
        elif isinstance(topics, list):
            result = []
            for item in topics:
                if isinstance(item, str) and ";" in item:
                    result.extend([t.strip() for t in item.split(";") if t.strip()])
                elif str(item).strip():
                    result.append(str(item).strip())
            return result
        return []

    def _ensure_user(self, user_id: str, role: str = "student"):
        """Garante que o usuário e seu perfil existam no banco."""
        if not user_id or not str(user_id).strip():
            return
            
        user_id = str(user_id).strip().lower()

        res = self.supabase.table("users").select("id").eq("id", user_id).execute()
        if not res.data:
            # 1. Cria na tabela pai 'users'
            self.supabase.table("users").insert({
                "id": user_id,
                "role": role
            }).execute()

            # 2. Cria na tabela correspondente ao perfil com nível padronizado
            if role == "student":
                self.supabase.table("students").insert({
                    "user_id": user_id,
                    "level": "a1",
                    "taught_words": []
                }).execute()
            elif role == "teacher":
                self.supabase.table("teachers").insert({
                    "user_id": user_id,
                    "department": "Inglês"
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
        level_clean = self._normalize_level(level)
        self.supabase.table("students").update({"level": level_clean, "current_module": module}).eq("user_id", user_id).execute()

    def get_user_profile(self, user_id: str):
        res = self.supabase.table("vw_user_students").select("*").eq("id", user_id).execute()
        if not res.data:
            return {}
        u = res.data[0]
        return {
            "level": self._normalize_level(u.get("level")),
            "module": u.get("current_module"),
            "created_at": u.get("created_at")
        }

    def get_learning_state(self, user_id: str):
        res = self.supabase.table("vw_user_students").select("level, current_module, last_topic, current_category, updated_at").eq("id", user_id).execute()
        if not res.data:
            return {}
        state = res.data[0]
        if "level" in state:
            state["level"] = self._normalize_level(state["level"])
        return state

    def update_learning_state(self, user_id: str, level=None, current_module=None, last_topic=None, current_category=None, **kwargs):
        self._ensure_user(user_id)
        payload = {}
        if level is not None: 
            payload["level"] = self._normalize_level(level)
        if current_module is not None: 
            payload["current_module"] = current_module
        if last_topic is not None: 
            payload["last_topic"] = last_topic
        if current_category is not None: 
            payload["current_category"] = current_category

        if payload:
            self.supabase.table("students").update(payload).eq("user_id", user_id).execute()

    def add_taught_word(self, user_id: str, word: str):
        """Adiciona uma palavra ao array 'taught_words' na tabela 'students'."""
        self._ensure_user(user_id)
        res = self.supabase.table("students").select("taught_words").eq("user_id", user_id).execute()
        words = (res.data[0].get("taught_words") or []) if res.data else []
        
        clean_word = word.lower().strip()
        if clean_word not in words:
            words.append(clean_word)
            self.supabase.table("students").update({"taught_words": words}).eq("user_id", user_id).execute()

    def get_taught_words(self, user_id: str):
        res = self.supabase.table("students").select("taught_words").eq("user_id", user_id).execute()
        if res.data and res.data[0].get("taught_words"):
            return res.data[0]["taught_words"]
        return []

    def list_classes(self, teacher_id="prof_01"):
        res = self.supabase.table("teacher_classes").select("id").eq("teacher_id", teacher_id).execute()
        return [Path(c["id"]) for c in (res.data or [])]

    def get_class(self, class_id: str, teacher_id: str = "prof_01"):
        res = (
            self.supabase.table("teacher_classes")
            .select("*")
            .eq("id", class_id)
            .eq("teacher_id", teacher_id)
            .execute()
        )
        if not res.data:
            return None

        c = res.data[0]
        return {
            "class_id": c["id"],
            "title": c.get("title"),
            "description": c.get("description"),
            "topics": self._parse_topics(c.get("topics"))
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
            "last_review": datetime.now(timezone.utc).isoformat()
        }
        if confidence is not None:
            payload["confidence"] = confidence

        self.supabase.table("topic_progress").upsert(payload, on_conflict="user_id, topic").execute()

    def get_pending_topics(self, user_id: str, class_id: str):
        class_info = self.get_class_by_id(class_id)
        if not class_info:
            return []

        all_topics = class_info.get("topics", [])
        progress = self.get_progress(user_id, class_id)

        pending = []
        for topic in all_topics:
            status = progress.get(topic, {}).get("status", "not_seen")
            if status != "mastered":
                pending.append({"topic": topic, "status": status})

        return pending

    def _mark_topic_presented(self, user_id: str, class_id: str, topic: str):
        class_data = self.get_class_by_id(class_id)
        if not class_data:
            return
        class_progress = self.get_progress(user_id, class_id)
        for official in class_data.get("topics", []):
            if topic.lower() in official.lower() or official.lower() in topic.lower():
                if official not in class_progress:
                    self.update_topic_progress(user_id, class_id, official, "presented")
                break

    def validate_turma(self, turma_code: str):
        res = self.supabase.table("turmas").select("*").eq("code", turma_code.strip().upper()).execute()
        return res.data[0] if res.data else None

    def register_or_login_student(self, username: str, turma_code: str = None):
        """
        Autentica o aluno. 
        Se ele já possui uma turma cadastrada, o turma_code não é obrigatório.
        """
        username = username.strip().lower()
        if turma_code:
            turma_code = turma_code.strip().upper()

        user_res = self.supabase.table("users").select("*").eq("id", username).execute()
        
        if user_res.data:
            user = user_res.data[0]
            if user.get("role") != "student":
                return False, "Este nome de usuário pertence a uma conta de Professor."
            
            st_res = (
                self.supabase.table("student_turmas")
                .select("turma_code, turmas(name)")
                .eq("student_id", username)
                .order("joined_at", desc=True)
                .execute()
            )
            enrolled_turmas = st_res.data or []

            if enrolled_turmas:
                if not turma_code:
                    active = enrolled_turmas[0]
                    t_code = active.get("turma_code")
                    t_name = active.get("turmas", {}).get("name") if active.get("turmas") else "Sua Turma"
                    return True, {
                        "user_id": username,
                        "role": "student",
                        "turma_code": t_code,
                        "turma_name": t_name
                    }
                else:
                    turma = self.validate_turma(turma_code)
                    if not turma:
                        return False, "Código de turma inválido. Verifique com seu professor."
                    
                    already_in = any(t["turma_code"] == turma_code for t in enrolled_turmas)
                    if not already_in:
                        self.supabase.table("student_turmas").insert({
                            "student_id": username,
                            "turma_code": turma_code
                        }).execute()
                    
                    return True, {
                        "user_id": username,
                        "role": "student",
                        "turma_code": turma_code,
                        "turma_name": turma.get("name")
                    }
            else:
                if not turma_code:
                    return False, "Você ainda não está em nenhuma turma. Por favor, informe o código da turma."
                
                turma = self.validate_turma(turma_code)
                if not turma:
                    return False, "Código de turma inválido."
                
                self.supabase.table("student_turmas").insert({
                    "student_id": username,
                    "turma_code": turma_code
                }).execute()

                return True, {
                    "user_id": username,
                    "role": "student",
                    "turma_code": turma_code,
                    "turma_name": turma.get("name")
                }

        else:
            if not turma_code:
                return False, "Primeiro acesso! Por favor, informe o código da turma fornecido pelo professor."
            
            turma = self.validate_turma(turma_code)
            if not turma:
                return False, "Código de turma inválido. Verifique com seu professor."

            self.supabase.table("users").insert({"id": username, "role": "student"}).execute()
            self.supabase.table("students").insert({"user_id": username, "level": "a1"}).execute()
            self.supabase.table("student_turmas").insert({
                "student_id": username,
                "turma_code": turma_code
            }).execute()

            return True, {
                "user_id": username,
                "role": "student",
                "turma_code": turma_code,
                "turma_name": turma.get("name")
            }

    def register_or_login_teacher(self, username: str, department: str = "Inglês"):
        username = username.strip().lower()

        user_res = self.supabase.table("users").select("*").eq("id", username).execute()
        if user_res.data:
            user = user_res.data[0]
            if user.get("role") != "teacher":
                return False, "Este nome de usuário pertence a uma conta de Aluno."
        else:
            self.supabase.table("users").insert({"id": username, "role": "teacher"}).execute()
            self.supabase.table("teachers").insert({"user_id": username, "department": department}).execute()

        return True, {"user_id": username, "role": "teacher"}

    def generate_turma_code(self, length: int = 6) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            res = self.supabase.table("turmas").select("code").eq("code", code).execute()
            if not res.data:
                return code

    def create_turma(self, teacher_id: str, name: str) -> dict:
        code = self.generate_turma_code()
        turma_id = f"turma_{code.lower()}"
        
        res = self.supabase.table("turmas").insert({
            "id": turma_id,
            "name": name,
            "code": code,
            "teacher_id": teacher_id
        }).execute()
        
        return res.data[0] if res.data else None

    def get_teacher_turmas(self, teacher_id: str) -> list:
        res = (
            self.supabase.table("turmas")
            .select("*")
            .eq("teacher_id", teacher_id)
            .order("created_at", desc=True)
            .execute()
        )
        turmas = res.data or []

        for turma in turmas:
            st_res = (
                self.supabase.table("student_turmas")
                .select("id", count="exact")
                .eq("turma_code", turma["code"])
                .execute()
            )
            turma["students_count"] = st_res.count if st_res.count is not None else len(st_res.data or [])

        return turmas

    def get_turma_details(self, turma_code: str, teacher_id: str) -> dict:
        t_res = (
            self.supabase.table("turmas")
            .select("*")
            .eq("code", turma_code)
            .eq("teacher_id", teacher_id)
            .execute()
        )
        if not t_res.data:
            return None
        
        turma = t_res.data[0]

        st_res = (
            self.supabase.table("student_turmas")
            .select("student_id, joined_at")
            .eq("turma_code", turma_code)
            .execute()
        )
        enrolled_students = st_res.data or []
        student_ids = [s["student_id"] for s in enrolled_students]

        students_progress = []
        if student_ids:
            profiles_res = (
                self.supabase.table("students")
                .select("user_id, level, current_module")
                .in_("user_id", student_ids)
                .execute()
            )
            profiles_map = {p["user_id"]: p for p in (profiles_res.data or [])}

            prog_res = (
                self.supabase.table("topic_progress")
                .select("user_id, topic, status, confidence")
                .in_("user_id", student_ids)
                .execute()
            )
            progress_data = prog_res.data or []

            for st in enrolled_students:
                uid = st["student_id"]
                prof = profiles_map.get(uid, {})
                user_topics = [p for p in progress_data if p["user_id"] == uid]
                mastered_count = sum(1 for t in user_topics if t.get("status") == "mastered")
                
                students_progress.append({
                    "student_id": uid,
                    "level": self._normalize_level(prof.get("level", "a1")),
                    "current_module": prof.get("current_module", "Geral"),
                    "joined_at": st.get("joined_at"),
                    "topics_count": len(user_topics),
                    "mastered_count": mastered_count
                })

        classes_res = (
            self.supabase.table("teacher_classes")
            .select("*")
            .eq("turma_id", turma["id"])
            .order("created_at", desc=True)
            .execute()
        )
        
        classes = classes_res.data or []
        for c in classes:
            c["topics"] = self._parse_topics(c.get("topics"))

        return {
            "turma": turma,
            "students": students_progress,
            "classes": classes
        }

    def add_turma_class_content(self, teacher_id: str, turma_id: str, title: str, description: str, topics) -> dict:
        """Cadastra uma nova aula/conteúdo garantindo o envio de lista de tópicos para colunas text[]."""
        class_id = f"class_{self.generate_turma_code(8).lower()}"
        topics_list = self._parse_topics(topics)
        
        res = self.supabase.table("teacher_classes").insert({
            "id": class_id,
            "teacher_id": teacher_id,
            "turma_id": turma_id,
            "title": title,
            "description": description,
            "topics": topics_list
        }).execute()
        
        return res.data[0] if res.data else None

    def get_classes_by_turma_code(self, turma_code: str) -> list:
        if not turma_code:
            return []
        
        turma_res = self.supabase.table("turmas").select("id").eq("code", turma_code.upper()).execute()
        if not turma_res.data:
            return []
        
        turma_id = turma_res.data[0]["id"]
        classes_res = self.supabase.table("teacher_classes").select("*").eq("turma_id", turma_id).execute()
        classes = classes_res.data or []
        
        for c in classes:
            c["topics"] = self._parse_topics(c.get("topics"))
            
        return classes

    def get_class_by_id(self, class_id: str) -> dict:
        res = self.supabase.table("teacher_classes").select("*").eq("id", class_id).execute()
        if not res.data:
            return None
        c = res.data[0]
        c["topics"] = self._parse_topics(c.get("topics"))
        return c