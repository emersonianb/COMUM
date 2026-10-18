import os
import json
from pypdf import PdfReader
from groq import Groq

class PDFProcessor:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não configurada no .env")
        self.client = Groq(api_key=api_key)

    def extract_text_from_pdf(self, file_stream) -> str:
        """Extrai o texto do PDF enviado no formulário."""
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()

    def extract_concepts_with_llm(self, pdf_text: str) -> dict:
        """Analisa o texto e retorna o JSON com o conteúdo da aula."""
        trimmed_text = pdf_text[:8000]

        prompt = f"""
Você é um assistente pedagógico. Analise o conteúdo do material escolar abaixo e extraia os principais tópicos e conceitos ensinados.

Responda EXCLUSIVAMENTE em formato JSON válido com a seguinte estrutura:
{{
  "title": "Título sugerido para a aula",
  "description": "Breve resumo do conteúdo da aula",
  "topics": ["Tópico 1", "Tópico 2", "Tópico 3"]
}}

Texto da aula:
\"\"\"
{trimmed_text}
\"\"\"
"""
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        return json.loads(content)