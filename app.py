import os
import urllib.parse
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "comum_secret_key_123")

# ==========================================================
# 🔑 LAZY INITIALIZATION (Evita estouro de timeout no Render)
# ==========================================================
_tutor = None
_content_agent = None
_pdf_processor = None
_memory_manager = None

def get_tutor():
    global _tutor
    if _tutor is None:
        from agent.core_2 import AgenticTutor
        _tutor = AgenticTutor()
    return _tutor

def get_content_agent():
    global _content_agent
    if _content_agent is None:
        from agent.content_agent import ContentAgent
        _content_agent = ContentAgent(memory=get_tutor().memory)
    return _content_agent

def get_pdf_processor():
    global _pdf_processor
    if _pdf_processor is None:
        from agent.pdf_processor import PDFProcessor
        _pdf_processor = PDFProcessor()
    return _pdf_processor

def get_memory_manager():
    global _memory_manager
    if _memory_manager is None:
        from agent.memory import MemoryManager
        _memory_manager = MemoryManager()
    return _memory_manager


# ==========================================================
# 📍 ROTAS DE NAVEGAÇÃO (PÁGINAS)
# ==========================================================

@app.route("/")
def index():
    """1. Landing Page institucional com a proposta do COMUM Agentic Tutor."""
    return render_template("index2.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = (request.form.get('username') or '').strip().lower()
    role = request.form.get('role', 'student')

    if not username:
        return render_template('login.html', error="Por favor, informe um nome de usuário válido.")

    memory_mgr = get_memory_manager()

    if role == 'teacher':
        success, res = memory_mgr.register_or_login_teacher(username)
        if not success:
            return render_template('login.html', error=res)
        session['user_id'] = username
        session['role'] = 'teacher'
        return redirect('/teacher/dashboard')
    
    else:  # student
        memory_mgr._ensure_user(username, role="student")
        session['user_id'] = username
        session['role'] = 'student'
        return redirect('/select-cards')


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/join-turma', methods=['POST'])
def join_turma():
    user_id = session.get('user_id')
    turma_code = request.form.get('turma_code')

    if not user_id:
        return redirect('/login')

    memory_mgr = get_memory_manager()
    turma = memory_mgr.validate_turma(turma_code)
    if not turma:
        return render_template('select-cards.html', error_msg="Código de sala inválido. Verifique com seu professor.")

    memory_mgr.supabase.table("student_turmas").upsert(
        {"student_id": user_id, "turma_code": turma["code"]},
        on_conflict="student_id, turma_code"
    ).execute()

    return redirect('/select-cards')


@app.route("/select-cards")
def select_cards():
    """3. Tela de seleção de aulas/cards consultando o Supabase pelo código da sala do aluno."""
    user_id = session.get("user_id")
    turma_code = session.get("turma_code")

    if not user_id or session.get("role") != "student":
        return redirect(url_for("login"))

    raw_classes = get_tutor().memory.get_classes_by_turma_code(turma_code)
    classes = []

    for c in raw_classes:
        classes.append({
            "id": c.get("id"),
            "class_id": c.get("id"),
            "title": c.get("title", "Aula sem Título"),
            "description": c.get("description", "Acesse para iniciar o diagnóstico e o chat."),
            "topics": c.get("topics", []),
            "code": f"Sala: {turma_code}"
        })

    return render_template("select_cards.html", classes=classes, turma_code=turma_code)


@app.route("/brainstorm/<class_id>")
def brainstorm_page(class_id):
    """5. Tela da Nuvem de Palavras (Diagnóstico Inicial com dados da aula selecionada)."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    class_data = get_tutor().memory.get_class_by_id(class_id)
    
    if class_data:
        title = class_data.get("title", f"Aula {class_id}")
        topics = class_data.get("topics", [])
    else:
        roadmap = get_content_agent().build_brainstorm_roadmap(user_id=user_id, teacher_id="prof_01", class_id=class_id)
        title = roadmap.get("title", f"Aula {class_id}")
        topics = roadmap.get("topics", [])

    return render_template("brainstorm.html", title=title, class_id=class_id, topics=topics)


@app.route("/chat/<class_id>")
def chat_page(class_id):
    """6. Tela do Messenger (Chat do Tutor Inteligente)."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    topics_queue = session.get("topics_queue", [])
    selected_topics = [t["name"] if isinstance(t, dict) else t for t in topics_queue]

    return render_template(
        "chat.html", 
        class_id=class_id, 
        topics_queue=topics_queue,
        selected_topics=selected_topics
    )


# ==========================================================
# ⚙️ ENDPOINTS DA API (DIAGNÓSTICO E CHAT COM PERSISTÊNCIA)
# ==========================================================

@app.route("/api/diagnostico", methods=["POST"])
def salvar_diagnostico():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Usuário não autenticado"}), 401

    data = request.json or {}
    class_id = data.get("class_id", "class_01")
    duvidas = data.get("duvidas", [])
    dominados = data.get("dominados", [])

    content_ag = get_content_agent()
    for d in duvidas:
        content_ag.record_diagnosis(user_id=user_id, class_id=class_id, topic=d, status="partial")
    for dom in dominados:
        content_ag.record_diagnosis(user_id=user_id, class_id=class_id, topic=dom, status="mastered")

    topics_queue = [{"name": d, "status": "duvida"} for d in duvidas]

    if not topics_queue:
        selected_topics = data.get("selected_topics", [])
        topics_queue = [{"name": st, "status": "revisao"} for st in selected_topics]

    if not topics_queue:
        return jsonify({"success": False, "message": "Nenhum tópico fornecido"}), 400

    session["topics_queue"] = topics_queue

    return jsonify({
        "success": True,
        "message": "Diagnóstico salvo com sucesso!",
        "redirect": f"/chat/{class_id}"
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Recebe as mensagens do aluno e processa via AgenticTutor repassando os tópicos da sessão."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Usuário não autenticado"}), 401

    data = request.json or {}
    user_message = data.get("message", "")
    class_id = data.get("class_id", "class_01")

    if not user_message:
        return jsonify({"status": "error", "message": "Mensagem vazia"}), 400

    try:
        topics_queue = session.get("topics_queue", [])

        ai_response = get_tutor().respond(
            user_id=user_id, 
            message=user_message, 
            class_id=class_id, 
            topics_queue=topics_queue
        )

        return jsonify({
            "status": "success",
            "response": ai_response
        })

    except Exception as e:
        print(f"🚨 ERRO NA RESPOSTA DO TUTOR: {e}")
        return jsonify({
            "status": "error",
            "message": f"Erro interno: {str(e)}"
        }), 500


def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "teacher" or not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# --- ROTAS DO PROFESSOR ---

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    teacher_id = session["user_id"]
    turmas = get_tutor().memory.get_teacher_turmas(teacher_id)
    
    total_students = sum(t.get("students_count", 0) for t in turmas)
    
    return render_template(
        "teacher_dashboard.html",
        teacher_id=teacher_id,
        turmas=turmas,
        total_turmas=len(turmas),
        total_students=total_students
    )


@app.route("/teacher/turma/create", methods=["POST"])
@teacher_required
def create_turma():
    teacher_id = session["user_id"]
    name = request.form.get("name", "").strip()
    
    if name:
        turma = get_tutor().memory.create_turma(teacher_id, name)
        flash(f"Sala '{name}' criada com sucesso! Código: {turma['code']}", "success")
    
    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/turma/<turma_code>")
@teacher_required
def view_turma(turma_code):
    teacher_id = session["user_id"]
    data = get_tutor().memory.get_turma_details(turma_code, teacher_id)
    
    if not data:
        return redirect(url_for("teacher_dashboard"))

    return render_template(
        "teacher_turma.html",
        teacher_id=teacher_id,
        turma=data["turma"],
        students=data["students"],
        classes=data["classes"]
    )


@app.route("/teacher/turma/<turma_code>/add-content", methods=["POST"])
@teacher_required
def add_turma_content(turma_code):
    teacher_id = session["user_id"]
    turma_id = request.form.get("turma_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    topics_raw = request.form.get("topics", "").strip()

    topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

    if title and turma_id:
        get_tutor().memory.add_turma_class_content(teacher_id, turma_id, title, description, topics)
        flash("Conteúdo adicionado à turma!", "success")

    return redirect(url_for("view_turma", turma_code=turma_code))


@app.route("/teacher/turma/<turma_code>/preview-content", methods=["POST"])
@teacher_required
def preview_turma_content(turma_code):
    print("\n--- [DEBUG] INICIANDO PROCESSAMENTO DE AULA ---")
    teacher_id = session["user_id"]
    turma_id = request.form.get("turma_id")
    description = request.form.get("description", "").strip()
    pdf_file = request.files.get("pdf_file")

    pdf_proc = get_pdf_processor()
    extracted_text = ""
    if pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith(".pdf"):
        print(f"[DEBUG] Arquivo PDF detectado: {pdf_file.filename}")
        extracted_text = pdf_proc.extract_text_from_pdf(pdf_file)
        print(f"[DEBUG] Caracteres extraídos do PDF: {len(extracted_text)}")

    text_to_process = extracted_text or description

    if not text_to_process:
        flash("Selecione um arquivo PDF ou digite um texto para processar.", "error")
        return redirect(url_for("view_turma", turma_code=turma_code))

    try:
        ai_result = pdf_proc.extract_concepts_with_llm(text_to_process)
        
        return render_template(
            "teacher_review.html",
            turma_code=turma_code,
            turma_id=turma_id,
            suggested_title=ai_result.get("title", ""),
            suggested_description=ai_result.get("description", ""),
            suggested_topics=", ".join(ai_result.get("topics", []))
        )
    except Exception as e:
        flash(f"Erro ao processar conteúdo com IA: {e}", "error")
        return redirect(url_for("view_turma", turma_code=turma_code))


@app.route("/teacher/turma/<turma_code>/save-content", methods=["POST"])
@teacher_required
def save_turma_content(turma_code):
    teacher_id = session["user_id"]
    turma_id = request.form.get("turma_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    topics_raw = request.form.get("topics", "").strip()

    topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

    if title and turma_id:
        get_tutor().memory.add_turma_class_content(teacher_id, turma_id, title, description, topics)
        flash("Aula aprovada e gravada com sucesso!", "success")

    return redirect(url_for("view_turma", turma_code=turma_code))


# ==========================================================
# 🎮 ENDPOINTS DE FLASHCARDS E MINI-GAMES DINÂMICOS (IA)
# ==========================================================

@app.route("/api/flashcards/<class_id>", methods=["GET"])
def get_flashcards(class_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Não autenticado"}), 401

    topics_queue = session.get("topics_queue", [])
    doubt_topics = [t["name"] if isinstance(t, dict) else t for t in topics_queue]

    class_data = get_tutor().memory.get_class_by_id(class_id) or {}
    class_title = class_data.get("title", "Aula de Inglês")

    data = get_content_agent().generate_student_flashcards(class_title, doubt_topics)
    return jsonify({"success": True, "flashcards": data.get("flashcards", [])})


@app.route("/api/minigame/<class_id>", methods=["GET"])
def get_minigame(class_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Não autenticado"}), 401

    topics_queue = session.get("topics_queue", [])
    doubt_topics = [t["name"] if isinstance(t, dict) else t for t in topics_queue]

    class_data = get_tutor().memory.get_class_by_id(class_id) or {}
    class_title = class_data.get("title", "Aula de Inglês")

    game_data = get_content_agent().generate_student_minigame(class_title, doubt_topics)
    return jsonify({"success": True, "game": game_data})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)