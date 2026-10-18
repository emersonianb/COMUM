import json
import os
from datetime import datetime
from pathlib import Path
import pymupdf as fitz
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings

class MaterialFormatter:
    def __init__(self, model="openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            model=model,
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )

    def format(self, raw_text):
        prompt = f"""
        Você é um formatador de conteúdo. Extraia do texto abaixo:

        - "tema": uma frase curta explicando o tema.
        - "conteudo": o conteúdo puro.

        Retorne SOMENTE um JSON válido:
        {{
        "tema": "...",
        "conteudo": "..."
        }}

        Texto:
        {raw_text}
        """
        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        try:
            return json.loads(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}") + 1
            return json.loads(content[start:end])


class MaterialManager:
    def __init__(self, memory_manager, formatter=None):
        self.memory_manager = memory_manager
        self.formatter = formatter
        # Modelo para geração dos vetores para o Supabase (pgvector)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

    def _extract_text_from_file(self, file_path):
        """Lê e extrai o texto de arquivos .pdf, .txt ou .md."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        ext = path.suffix.lower()

        if ext == ".pdf":
            text = ""
            with fitz.open(path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        elif ext in [".txt", ".md"]:
            return path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Formato '{ext}' não suportado. Use .pdf, .txt ou .md.")

    def add_material(self, user_id, category, raw_text):
        """Formata o texto bruto, gera o embedding vetorial e salva no Supabase."""
        category_clean = category.lower()
        self.memory_manager._ensure_user(user_id)

        if self.formatter:
            structured = self.formatter.format(raw_text)
        else:
            structured = {"tema": "Indefinido", "conteudo": raw_text}

        topic = structured.get("tema", "Indefinido")
        content = structured.get("conteudo", raw_text)

        # Gera o vetor vetorial para permitir busca por RAG
        vector = self.embeddings.embed_query(content)

        res = self.memory_manager.supabase.table("user_materials").insert({
            "user_id": user_id,
            "category": category_clean,
            "topic": topic,
            "content": content,
            "embedding": vector
        }).execute()

        material_id = res.data[0]["id"] if res.data else None

        return {
            "id": material_id,
            "category": category_clean,
            "topic": topic,
            "status": "salvo_no_banco"
        }

    def add_material_from_file(self, user_id, category, file_path):
        """Extrai o texto de um PDF/TXT no disco, formata via LLM e salva no banco."""
        raw_text = self._extract_text_from_file(file_path)
        return self.add_material(user_id, category, raw_text)

    def get_materials_by_category(self, user_id, category):
        """Recupera os materiais cadastrados de uma categoria específica para o usuário."""
        res = (
            self.memory_manager.supabase.table("user_materials")
            .select("id, topic, content, created_at")
            .eq("user_id", user_id)
            .eq("category", category.lower())
            .execute()
        )
        return res.data or []