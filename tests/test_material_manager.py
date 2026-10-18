import pytest
import pymupdf as fitz
from agent.material_manager import MaterialManager

class FakeFormatter:
    def format(self, raw_text):
        return {"tema": "Tema Extraído Automatizado", "conteudo": raw_text}

@pytest.fixture
def material_manager(memory_manager):
    return MaterialManager(memory_manager=memory_manager, formatter=FakeFormatter())

@pytest.fixture
def user_id():
    return "user_test_mat_mgr_diverse"

def test_add_material_text(material_manager, user_id):
    """Testa inserção direta de texto com vetorização."""
    res = material_manager.add_material(user_id, "gramatica", "Present Perfect uses have/has + past participle.")
    assert res["id"] is not None
    assert res["status"] == "salvo_no_banco"

def test_add_material_from_txt_file(material_manager, user_id, tmp_path):
    """Testa extração e ingestão de arquivo TXT."""
    txt_file = tmp_path / "lesson.txt"
    txt_file.write_text("At the airport: gate, boarding pass, luggage.", encoding="utf-8")

    res = material_manager.add_material_from_file(user_id, "vocabulario", str(txt_file))
    assert res["id"] is not None
    assert res["category"] == "vocabulario"

def test_add_material_from_pdf_file(material_manager, user_id, tmp_path):
    """Testa a geração e parsing real de um documento PDF via PyMuPDF (fitz)."""
    pdf_path = tmp_path / "documento_aula.pdf"
    
    # Cria um PDF real em memória
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "PDF Material: Conditional Sentences (If Clauses).")
    doc.save(str(pdf_path))
    doc.close()

    res = material_manager.add_material_from_file(user_id, "gramatica", str(pdf_path))
    assert res["id"] is not None
    assert res["status"] == "salvo_no_banco"

def test_unsupported_file_extension(material_manager, user_id, tmp_path):
    """Garante que formatos não suportados (.docx, .png) lançam ValueError."""
    unsupported = tmp_path / "image.png"
    unsupported.write_text("fake image content")

    with pytest.raises(ValueError, match="Formato '.png' não suportado"):
        material_manager.add_material_from_file(user_id, "geral", str(unsupported))

def test_nonexistent_file_exception(material_manager, user_id):
    """Garante que a tentativa de leitura de arquivo inexistente lança FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        material_manager.add_material_from_file(user_id, "geral", "caminho/inexistente/aula.pdf")

def test_category_isolation(material_manager, user_id):
    """Garante que a busca por categoria isola estritamente os materiais de categorias distintas."""
    material_manager.add_material(user_id, "pronuncia", "Th sound pronunciation guide.")
    
    pronunciation_mats = material_manager.get_materials_by_category(user_id, "pronuncia")
    grammar_mats = material_manager.get_materials_by_category(user_id, "outra_categoria_inexistente")

    assert len(pronunciation_mats) > 0
    assert len(grammar_mats) == 0