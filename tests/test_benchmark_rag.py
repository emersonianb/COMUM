import os
import json
import time
from agent.rag import GuideRAG
from agent.llm_handler import LLMHandler
from agent.memory import MemoryManager

TEST_USER_ID = "test_bench_user_expanded"

BENCHMARK_QUESTIONS = [
    {
        "query": "Como o professor recomenda praticar o Present Perfect?",
        "category": "gramatica",
        "topic": "Present Perfect",
        "content": "Para praticar o Present Perfect, o professor recomenda focar em experiências pessoais passadas sem especificar a data exata.",
        "expected_fact": "experiências pessoais"
    },
    {
        "query": "Qual a diferença entre 'borrow' e 'lend' segundo a nota de aula?",
        "category": "vocabulario",
        "topic": "Borrow vs Lend",
        "content": "A diferença é que borrow significa pegar emprestado de alguém, enquanto lend significa emprestar ou dar algo temporariamente.",
        "expected_fact": "pegar emprestado"
    },
    {
        "query": "Como usar a Terceira Condicional (Third Conditional)?",
        "category": "gramatica",
        "topic": "Third Conditional",
        "content": "A Terceira Condicional usa 'if + past perfect' seguido de 'would have + past participle' para situações hipotéticas no passado.",
        "expected_fact": "would have"
    },
    {
        "query": "O que significa a expressão 'break a leg' na nota de aula?",
        "category": "expressoes",
        "topic": "Idioms",
        "content": "A expressão 'break a leg' é uma forma de desejar boa sorte a alguém antes de uma apresentação.",
        "expected_fact": "boa sorte"
    },
    {
        "query": "Qual a regra para a pronúncia do terminação '-ed' no passado?",
        "category": "pronuncia",
        "topic": "Past Endings",
        "content": "A terminação '-ed' soa como /id/ apenas após verbos terminados com os sons de T ou D.",
        "expected_fact": "sons de t ou d"
    }
]

def seed_test_materials(memory_manager, rag_agent):
    memory_manager._ensure_user(TEST_USER_ID)
    for item in BENCHMARK_QUESTIONS:
        try:
            vector = rag_agent.embeddings.embed_query(item["content"])
            memory_manager.supabase.table("user_materials").upsert({
                "user_id": TEST_USER_ID,
                "category": item["category"],
                "topic": item["topic"],
                "content": item["content"],
                "embedding": vector
            }).execute()
        except Exception as e:
            print(f"Aviso ao inserir material de teste: {e}")

def test_comparative_benchmark():
    print("\n🚀 Iniciando Benchmark Comparativo Expandido (5 Cenários)")
    
    memory_manager = MemoryManager()
    rag_agent = GuideRAG(user_id=TEST_USER_ID)
    llm = LLMHandler()

    seed_test_materials(memory_manager, rag_agent)
    rag_agent.query(question="warmup", k=1)

    results = []

    for item in BENCHMARK_QUESTIONS:
        query = item["query"]
        expected_fact = item["expected_fact"].lower()

        # 1. Busca Direta
        start_a = time.perf_counter()
        resp_direct = llm.generate("Você é um tutor de inglês. Responda objetivamente.", query)
        time_direct = (time.perf_counter() - start_a) * 1000

        # 2. Busca RAG
        start_vector = time.perf_counter()
        context = rag_agent.query(question=query, k=3)
        time_vector = (time.perf_counter() - start_vector) * 1000

        start_llm_rag = time.perf_counter()
        sys_prompt_b = f"Você é um tutor de inglês. Responda com base estritamente no contexto abaixo:\n{context}"
        resp_rag = llm.generate(sys_prompt_b, query)
        time_llm_rag = (time.perf_counter() - start_llm_rag) * 1000

        total_rag_time = time_vector + time_llm_rag

        direct_text = resp_direct[0] if isinstance(resp_direct, tuple) else resp_direct
        rag_text = resp_rag[0] if isinstance(resp_rag, tuple) else resp_rag

        results.append({
            "query": query,
            "category": item["category"],
            "direct_latency_ms": round(time_direct, 2),
            "vector_search_ms": round(time_vector, 2),
            "rag_llm_latency_ms": round(time_llm_rag, 2),
            "total_rag_latency_ms": round(total_rag_time, 2),
            "direct_correct": expected_fact in str(direct_text).lower(),
            "rag_correct": expected_fact in str(rag_text).lower()
        })

    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))

    assert len(results) == 5
    assert all(r["vector_search_ms"] < 2000 for r in results)

if __name__ == "__main__":
    test_comparative_benchmark()