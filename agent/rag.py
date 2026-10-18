from langchain_huggingface import HuggingFaceEmbeddings
from agent.memory import MemoryManager

class GuideRAG:
    def __init__(self, user_id, categoria=None, max_items=5, memory_manager=None):
        self.user_id = user_id
        self.categoria = categoria.lower() if categoria else None
        self.max_items = max_items
        self.memory = memory_manager or MemoryManager()
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

    def query(self, question, k=3, match_threshold=0.25):
        # 1. Gera o vetor da pergunta feita pelo usuário
        query_vector = self.embeddings.embed_query(question)

        # 2. Executa a busca vetorial via RPC no Supabase
        res = self.memory.supabase.rpc(
            'match_materials',
            {
                'query_embedding': query_vector,
                'match_threshold': 0.25,
                'match_count': k or self.max_items,
                'p_user_id': self.user_id,
                'p_category': self.categoria
            }
        ).execute()

        matches = res.data or []
        if not matches:
            return ""

        # 3. Agrupa os trechos encontrados para o Prompt
        text = ""
        for m in matches:
            text += f"\nTema: {m.get('topic')}\n{m.get('content')}\n"

        return text.strip()