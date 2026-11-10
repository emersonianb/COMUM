
import os
import numpy as np
from google import genai
from google.genai import types

from agent.memory import MemoryManager


class GuideRAG:
    def __init__(
        self,
        user_id,
        categoria=None,
        max_items=5,
        memory_manager=None,
        class_id=None
    ):
        self.user_id = user_id
        self.categoria = categoria.lower() if categoria else None
        self.max_items = max_items
        self.memory = memory_manager or MemoryManager()
        self.class_id = class_id

        # Cliente da API Gemini
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

    def _generate_embedding(self, text):
        """Gera embedding da consulta usando Gemini."""

        response = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=384
            )
        )

        vector = np.array(
            response.embeddings[0].values,
            dtype=np.float32
        )

        # Normaliza o vetor
        norm = np.linalg.norm(vector)

        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    def query(self, question, k=3, match_threshold=0.25):
        # 1. Gera o embedding da pergunta do aluno
        query_vector = self._generate_embedding(question)

        # 2. Executa a busca vetorial via RPC no Supabase
        res = self.memory.supabase.rpc('match_materials', {
            'query_embedding': query_vector,
            'match_threshold': match_threshold,
            'match_count': k or self.max_items,
            'p_user_id': self.user_id,
            'p_category': self.categoria,
            'p_class_id': self.class_id
        }).execute()

        matches = res.data or []

        if not matches:
            return ""

        # 3. Agrupa os trechos encontrados para o prompt
        text = ""

        for m in matches:
            text += (
                f"\nTema: {m.get('topic')}\n"
                f"{m.get('content')}\n"
            )

        return text.strip()
