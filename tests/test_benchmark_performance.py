import os
import time
import json
import asyncio
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Configurações do Teste
MODEL_NAME = "openai/gpt-oss-120b" # Ajuste para o nome exato do modelo utilizado
NUM_TRIALS = 10 # Número de repetições por cenário
CONCURRENCY_LEVELS = [1, 5, 10] # Requisições simultâneas

PROMPTS = {
    "Curto (50 tokens)": "Explain the difference between 'make' and 'do' in English in two simple sentences.",
    "Médio (250 tokens)": "Explain the concept of present perfect tense in English grammar. Provide three practical examples with explanations of why this tense is used in each case.",
    "Longo (700 tokens)": "Provide a comprehensive guide on English preposition usage (in, on, at) for Portuguese speakers. Include rules for time and place, common pitfalls, false friends, and 10 exercise sentences with answer keys."
}

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def measure_single_request(prompt_label, prompt_text):
    start_time = time.perf_counter()
    ttft = None
    token_times = []
    generated_tokens = 0
    
    # Executa a chamada em thread separada para não bloquear o loop assíncrono
    def call_stream():
        nonlocal ttft, generated_tokens
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Ou o endpoint configurado na Groq
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.4,
            stream=True
        )
        
        first_token = True
        for chunk in completion:
            now = time.perf_counter()
            content = chunk.choices[0].delta.content or ""
            if content:
                if first_token:
                    ttft = (now - start_time) * 1000 # em milissegundos
                    first_token = False
                token_times.append(now)
                generated_tokens += 1
                
    await asyncio.to_thread(call_stream)
    
    total_time = token_times[-1] - start_time if token_times else 0
    generation_time = token_times[-1] - token_times[0] if len(token_times) > 1 else 0.001
    
    tps = generated_tokens / generation_time if generation_time > 0 else 0
    tbt = (generation_time / (generated_tokens - 1) * 1000) if generated_tokens > 1 else 0
    
    return {
        "prompt_label": prompt_label,
        "ttft_ms": ttft or 0,
        "tps": tps,
        "tbt_ms": tbt,
        "total_latency_ms": total_time * 1000,
        "tokens": generated_tokens
    }

async def run_benchmark():
    print("🚀 Iniciando Teste de Carga e Latência (Groq LPU)...")
    results = []
    
    for label, prompt in PROMPTS.items():
        print(f"\nAvaliando cenário: {label}")
        for conc in CONCURRENCY_LEVELS:
            print(f"  -> Concorrência: {conc} requisição(ões) simultânea(s)...")
            tasks = [measure_single_request(label, prompt) for _ in range(conc)]
            batch_results = await asyncio.gather(*tasks)
            for res in batch_results:
                res["concurrency"] = conc
                results.append(res)
                
    # Salva os resultados em arquivo JSON
    os.makedirs("data", exist_ok=True)
    with open("data/benchmark_llm_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print("\n✅ Teste de latência concluído com sucesso! Dados salvos em 'data/benchmark_llm_results.json'.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())