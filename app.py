
import os
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, flash, get_flashed_messages, make_response
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "comum_secret_key_123")


# ==========================================================
# LAZY INITIALIZATION
# Evita inicializar agentes e conexões durante o boot do Render
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
# FUNÇÕES AUXILIARES
# ==========================================================

def parse_topics(topics_raw: str) -> list:
    """Divide tópicos preferencialmente por ponto e vírgula ou quebras de linha."""
    if not topics_raw:
        return []

    normalized = topics_raw.replace("\r\n", ";").replace("\n", ";")
    delimiter = ";" if ";" in normalized else ","

    return [
        topic.strip()
        for topic in normalized.split(delimiter)
        if topic.strip()
    ]


def database_error_response(username="", role="student"):
    """Resposta amigável quando o Supabase está indisponível."""
    return render_template(
        "login.html",
        error=(
            "Não foi possível conectar ao sistema no momento. "
            "Tente novamente em alguns minutos."
        ),
        username=username,
        role=role
    ), 503


# ==========================================================
# ROTAS DE NAVEGAÇÃO
# ==========================================================

@app.route("/")
def index():
    return render_template("index2.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        session.clear()

        response = make_response(render_template("login.html"))
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"

        return response

    username = (request.form.get("username") or "").strip().lower()
    role = request.form.get("role", "student")

    if role not in ("student", "teacher"):
        role = "student"

    if not username:
        return render_template(
            "login.html",
            error="Por favor, informe um nome de usuário válido.",
            username=username,
            role=role
        )

    # Importação sob demanda: não interfere no boot do Render.
    from agent.memory import DatabaseUnavailableError

    try:
        memory_mgr = get_memory_manager()

        if role == "teacher":

            success, result = memory_mgr.register_or_login_teacher(username)

            if not success:
                return render_template(
                    "login.html",
                    error=result,
                    username=username,
                    role=role
                )

            session.clear()
            session["user_id"] = username
            session["role"] = "teacher"

            return redirect(url_for("teacher_dashboard"))

        # Login de estudante: garante que o usuário exista.
        memory_mgr._ensure_user(username, role="student")

        # Consulta as turmas antes de criar a sessão.
        result = memory_mgr._execute(
            memory_mgr.supabase.table("student_turmas")
            .select("turma_code")
            .eq("student_id", username)
        )

        student_turmas = [
            turma["turma_code"]
            for turma in (result.data or [])
            if turma.get("turma_code")
        ]

        session.clear()
        session["user_id"] = username
        session["role"] = "student"
        session["student_turmas"] = student_turmas

        return redirect(url_for("select_cards"))

    except DatabaseUnavailableError:
        return render_template(
            "login.html",
            error=(
                "Não foi possível conectar ao banco de dados. "
                "O serviço pode estar temporariamente indisponível. "
                "Tente novamente mais tarde."
            ),
            username=username,
            role=role
        ), 503

    except ValueError:
        app.logger.exception(
            "Erro na configuração do MemoryManager durante o login."
        )
        return render_template(
            "login.html",
            error=(
                "O serviço está temporariamente indisponível. "
                "Tente novamente mais tarde."
            ),
            username=username,
            role=role
        ), 503


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/join-turma", methods=["POST"])
def join_turma():

    user_id = session.get("user_id")
    turma_code = (request.form.get("turma_code") or "").strip().upper()

    if not user_id:
        return redirect(url_for("login"))

    try:
        memory_mgr = get_memory_manager()
        turma = memory_mgr.validate_turma(turma_code)

        if not turma:
            flash(
                "Código de sala inválido. Verifique com seu professor.",
                "error"
            )
            return redirect(url_for("select_cards"))

        code = turma.get("code", turma_code).upper()

        memory_mgr._execute(
            memory_mgr.supabase.table("student_turmas").upsert(
                {
                    "student_id": user_id,
                    "turma_code": code
                },
                on_conflict="student_id, turma_code"
            )
        )

        user_turmas = session.get("student_turmas", [])

        if code not in user_turmas:
            user_turmas.append(code)

        session["student_turmas"] = user_turmas
        session["turma_code"] = code
        session.modified = True

        flash(
            f"Você entrou na sala '{turma.get('name', code)}' com sucesso!",
            "success"
        )

    except Exception:
        app.logger.exception("Erro ao entrar na turma.")
        flash(
            "Não foi possível entrar na sala. Tente novamente mais tarde.",
            "error"
        )

    return redirect(url_for("select_cards"))


@app.route("/select-cards")
def select_cards():

    user_id = session.get("user_id")

    if not user_id or session.get("role") != "student":
        return redirect(url_for("login"))

    try:
        memory_mgr = get_memory_manager()
        tutor_obj = get_tutor()

        turma_codes = set()

        if isinstance(session.get("student_turmas"), list):
            turma_codes.update(session["student_turmas"])

        if session.get("turma_code"):
            turma_codes.add(session["turma_code"])

        # Sincroniza as turmas com o Supabase.
        try:
            result = memory_mgr._execute(
                memory_mgr.supabase.table("student_turmas")
                .select("turma_code")
                .eq("student_id", user_id)
            )

            db_codes = [
                turma["turma_code"]
                for turma in (result.data or [])
                if turma.get("turma_code")
            ]

            turma_codes.update(db_codes)
            session["student_turmas"] = list(turma_codes)
            session.modified = True

        except Exception:
            app.logger.exception(
                "Não foi possível sincronizar as turmas do estudante."
            )

        classes = []

        for code in turma_codes:
            raw_classes = tutor_obj.memory.get_classes_by_turma_code(code)

            for item in raw_classes:
                classes.append({
                    "id": item.get("id"),
                    "class_id": item.get("id"),
                    "title": item.get("title", "Aula sem Título"),
                    "description": item.get(
                        "description",
                        "Acesse para iniciar o diagnóstico e o chat."
                    ),
                    "topics": item.get("topics", []),
                    "code": f"Sala: {code}"
                })

        flashes = get_flashed_messages(with_categories=True)

        success_msg = next(
            (msg for category, msg in flashes if category == "success"),
            None
        )
        error_msg = next(
            (msg for category, msg in flashes if category == "error"),
            None
        )

        try:
            return render_template(
                "select_cards.html",
                classes=classes,
                success_msg=success_msg,
                error_msg=error_msg
            )
        except Exception:
            return render_template(
                "select-cards.html",
                classes=classes,
                success_msg=success_msg,
                error_msg=error_msg
            )

    except Exception:
        app.logger.exception("Erro ao carregar a seleção de aulas.")
        return (
            "Não foi possível carregar suas aulas no momento. "
            "Tente novamente mais tarde."
        ), 503


@app.route("/brainstorm/<class_id>")
def brainstorm_page(class_id):

    user_id = session.get("user_id")

    if not user_id or session.get("role") != "student":
        return redirect(url_for("login"))

    try:
        class_data = get_tutor().memory.get_class_by_id(class_id)

        if not class_data:
            return "Aula não encontrada.", 404

        title = class_data.get("title") or f"Aula {class_id}"
        topics = class_data.get("topics") or []

        if not isinstance(topics, list):
            app.logger.error(
                "Formato inválido de tópicos para a aula %s", class_id
            )
            return "Não foi possível carregar os tópicos desta aula.", 500

        return render_template(
            "brainstorm.html",
            title=title,
            class_id=class_id,
            topics=topics
        )

    except Exception:
        app.logger.exception("Erro ao carregar a página de diagnóstico.")
        return "Não foi possível carregar esta aula.", 503


@app.route("/chat/<class_id>")
def chat_page(class_id):

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    topics_queue = session.get("topics_queue", [])

    selected_topics = [
        topic["name"] if isinstance(topic, dict) else topic
        for topic in topics_queue
    ]

    return render_template(
        "chat.html",
        class_id=class_id,
        topics_queue=topics_queue,
        selected_topics=selected_topics
    )


# ==========================================================
# ENDPOINTS DA API: DIAGNÓSTICO E CHAT
# ==========================================================

@app.route("/api/diagnostico", methods=["POST"])
def salvar_diagnostico():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Usuário não autenticado"
        }), 401

    data = request.json or {}

    class_id = data.get("class_id", "class_01")
    duvidas = data.get("duvidas", [])
    dominados = data.get("dominados", [])

    try:
        content_ag = get_content_agent()

        for topic in duvidas:
            content_ag.record_diagnosis(
                user_id=user_id,
                class_id=class_id,
                topic=topic,
                status="partial"
            )

        for topic in dominados:
            content_ag.record_diagnosis(
                user_id=user_id,
                class_id=class_id,
                topic=topic,
                status="mastered"
            )

        topics_queue = [
            {"name": topic, "status": "duvida"}
            for topic in duvidas
        ]

        if not topics_queue:
            selected_topics = data.get("selected_topics", [])
            topics_queue = [
                {"name": topic, "status": "revisao"}
                for topic in selected_topics
            ]

        if not topics_queue:
            return jsonify({
                "success": False,
                "message": "Nenhum tópico fornecido"
            }), 400

        session["topics_queue"] = topics_queue
        session["chat_started"] = False

        return jsonify({
            "success": True,
            "message": "Diagnóstico salvo com sucesso!",
            "redirect": f"/chat/{class_id}"
        })

    except Exception:
        app.logger.exception("Erro ao salvar diagnóstico.")

        return jsonify({
            "success": False,
            "message": "Não foi possível salvar o diagnóstico."
        }), 503


@app.route("/api/chat", methods=["POST"])
def api_chat():

    user_id = session.get("user_id")
    is_new_session = not session.get("chat_started", False)

    if not user_id:
        return jsonify({
            "status": "error",
            "message": "Usuário não autenticado"
        }), 401

    data = request.json or {}

    user_message = data.get("message", "")
    class_id = data.get("class_id", "class_01")

    if not user_message:
        return jsonify({
            "status": "error",
            "message": "Mensagem vazia"
        }), 400

    try:
        topics_queue = session.get("topics_queue", [])

        ai_response = get_tutor().respond(
            user_id=user_id,
            message=user_message,
            class_id=class_id,
            topics_queue=topics_queue,
            is_new_session=is_new_session
        )

        session["chat_started"] = True

        return jsonify({
            "status": "success",
            "response": ai_response
        })

    except Exception:
        app.logger.exception("Erro na resposta do tutor.")

        return jsonify({
            "status": "error",
            "message": (
                "O tutor está temporariamente indisponível. "
                "Tente novamente."
            )
        }), 503


# ==========================================================
# AUTENTICAÇÃO DE PROFESSORES
# ==========================================================

def teacher_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get("role") != "teacher" or not session.get("user_id"):
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# ==========================================================
# ROTAS DO PROFESSOR
# ==========================================================

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():

    teacher_id = session["user_id"]

    try:
        turmas = get_tutor().memory.get_teacher_turmas(teacher_id)

        total_students = sum(
            turma.get("students_count", 0)
            for turma in turmas
        )

        return render_template(
            "teacher_dashboard.html",
            teacher_id=teacher_id,
            turmas=turmas,
            total_turmas=len(turmas),
            total_students=total_students
        )

    except Exception:
        app.logger.exception("Erro ao carregar painel do professor.")
        flash("Não foi possível carregar o painel.", "error")
        return "Serviço temporariamente indisponível.", 503


@app.route("/teacher/turma/create", methods=["POST"])
@teacher_required
def create_turma():

    teacher_id = session["user_id"]
    name = request.form.get("name", "").strip()

    if name:
        try:
            turma = get_tutor().memory.create_turma(teacher_id, name)
            flash(
                f"Sala '{name}' criada com sucesso! Código: {turma['code']}",
                "success"
            )
        except Exception:
            app.logger.exception("Erro ao criar turma.")
            flash("Não foi possível criar a sala.", "error")

    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/turma/<turma_code>")
@teacher_required
def view_turma(turma_code):

    teacher_id = session["user_id"]

    try:
        data = get_tutor().memory.get_turma_details(
            turma_code,
            teacher_id
        )

        if not data:
            return redirect(url_for("teacher_dashboard"))

        return render_template(
            "teacher_turma.html",
            teacher_id=teacher_id,
            turma=data["turma"],
            students=data["students"],
            classes=data["classes"],
            preview_data=None
        )

    except Exception:
        app.logger.exception("Erro ao abrir turma.")
        return "Não foi possível carregar a turma.", 503


@app.route("/teacher/turma/<turma_code>/add-content", methods=["POST"])
@teacher_required
def add_turma_content(turma_code):

    teacher_id = session["user_id"]

    turma_id = request.form.get("turma_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    topics = parse_topics(request.form.get("topics", "").strip())

    if title and turma_id:
        try:
            get_tutor().memory.add_turma_class_content(
                teacher_id,
                turma_id,
                title,
                description,
                topics
            )
            flash("Conteúdo adicionado à turma!", "success")

        except Exception:
            app.logger.exception("Erro ao adicionar conteúdo.")
            flash("Não foi possível adicionar o conteúdo.", "error")

    return redirect(url_for("view_turma", turma_code=turma_code))


@app.route("/teacher/turma/<turma_code>/preview-content", methods=["POST"])
@teacher_required
def preview_turma_content(turma_code):

    teacher_id = session["user_id"]

    try:
        memory_mgr = get_memory_manager()
        data = memory_mgr.get_turma_details(turma_code, teacher_id)

        if not data:
            return redirect(url_for("teacher_dashboard"))

        turma_id = request.form.get("turma_id")
        description = request.form.get("description", "").strip()
        pdf_file = request.files.get("pdf_file")

        pdf_proc = get_pdf_processor()
        extracted_text = ""

        if (
            pdf_file
            and pdf_file.filename
            and pdf_file.filename.lower().endswith(".pdf")
        ):
            extracted_text = pdf_proc.extract_text_from_pdf(pdf_file)

        text_to_process = extracted_text or description

        if not text_to_process:
            flash(
                "Selecione um arquivo PDF ou digite um texto para processar.",
                "error"
            )
            return redirect(url_for("view_turma", turma_code=turma_code))

        ai_result = pdf_proc.extract_concepts_with_llm(text_to_process)

        raw_topics = ai_result.get("topics", [])

        topics_formatted = (
            " ; ".join(raw_topics)
            if isinstance(raw_topics, list)
            else str(raw_topics)
        )

        preview_data = {
            "turma_id": turma_id,
            "suggested_title": ai_result.get("title", ""),
            "suggested_description": ai_result.get("description", ""),
            "suggested_topics": topics_formatted,
            "raw_material_text": text_to_process
        }

        return render_template(
            "teacher_turma.html",
            teacher_id=teacher_id,
            turma=data["turma"],
            students=data["students"],
            classes=data["classes"],
            preview_data=preview_data
        )

    except Exception:
        app.logger.exception("Erro ao processar conteúdo com IA.")
        flash(
            "Não foi possível processar o conteúdo. Tente novamente.",
            "error"
        )
        return redirect(url_for("view_turma", turma_code=turma_code))


@app.route("/teacher/turma/<turma_code>/save-content", methods=["POST"])
@teacher_required
def save_turma_content(turma_code):
    teacher_id = session["user_id"]
    turma_id = request.form.get("turma_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    topics = parse_topics(request.form.get("topics", "").strip())
    raw_material_text = request.form.get("raw_material_text", "").strip()

    if title and turma_id:
        try:
            tutor = get_tutor()

            # 1. Salva os dados da aula
            saved_class = tutor.memory.add_turma_class_content(
                teacher_id,
                turma_id,
                title,
                description,
                topics
            )

            # 2. Obtém o ID da aula criada
            class_id = saved_class["id"]

            # 3. Salva o conteúdo original para recuperação pelo RAG
            if raw_material_text:
                tutor.material_manager.add_material(
                    user_id=teacher_id,
                    category="geral",
                    raw_text=raw_material_text,
                    class_id=class_id
                )

            flash("Aula gravada e adicionada à turma com sucesso!", "success")

        except Exception:
            app.logger.exception("Erro ao salvar aula ou material.")
            flash("Não foi possível salvar a aula e seu material.", "error")

    return redirect(url_for("view_turma", turma_code=turma_code))

@app.route(
    "/teacher/turma/<turma_code>/class/<class_id>/delete",
    methods=["POST"]
)
@teacher_required
def delete_turma_class(turma_code, class_id):

    try:
        memory_mgr = get_memory_manager()

        memory_mgr._execute(
            memory_mgr.supabase.table("teacher_classes")
            .delete()
            .eq("id", class_id)
        )

        flash("Aula removida com sucesso!", "success")

    except Exception:
        app.logger.exception("Erro ao excluir aula.")
        flash("Não foi possível excluir a aula.", "error")

    return redirect(url_for("view_turma", turma_code=turma_code))


@app.route(
    "/teacher/turma/<turma_code>/class/<class_id>/edit",
    methods=["POST"]
)
@teacher_required
def edit_turma_class(turma_code, class_id):

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    topics = parse_topics(request.form.get("topics", "").strip())

    try:
        memory_mgr = get_memory_manager()

        memory_mgr._execute(
            memory_mgr.supabase.table("teacher_classes")
            .update({
                "title": title,
                "description": description,
                "topics": topics
            })
            .eq("id", class_id)
        )

        flash("Aula atualizada com sucesso!", "success")

    except Exception:
        app.logger.exception("Erro ao atualizar aula.")
        flash("Não foi possível atualizar a aula.", "error")

    return redirect(url_for("view_turma", turma_code=turma_code))


@app.route("/teacher/turma/<turma_code>/delete", methods=["POST"])
@teacher_required
def delete_turma(turma_code):

    teacher_id = session["user_id"]

    try:
        memory_mgr = get_memory_manager()

        memory_mgr._execute(
            memory_mgr.supabase.table("student_turmas")
            .delete()
            .eq("turma_code", turma_code)
        )

        memory_mgr._execute(
            memory_mgr.supabase.table("turmas")
            .delete()
            .eq("code", turma_code)
            .eq("teacher_id", teacher_id)
        )

        flash(f"Turma {turma_code} excluída.", "success")

    except Exception:
        app.logger.exception("Erro ao excluir turma.")
        flash("Não foi possível excluir a turma.", "error")

    return redirect(url_for("teacher_dashboard"))


# ==========================================================
# FLASHCARDS E MINI-GAMES
# ==========================================================

@app.route("/api/flashcards/<class_id>", methods=["GET"])
def get_flashcards(class_id):

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Não autenticado"
        }), 401

    try:
        topics_queue = session.get("topics_queue", [])

        doubt_topics = [
            topic["name"] if isinstance(topic, dict) else topic
            for topic in topics_queue
        ]

        class_data = get_tutor().memory.get_class_by_id(class_id) or {}
        class_title = class_data.get("title", "Aula de Inglês")

        data = get_content_agent().generate_student_flashcards(
            class_title,
            doubt_topics
        )

        return jsonify({
            "success": True,
            "flashcards": data.get("flashcards", [])
        })

    except Exception:
        app.logger.exception("Erro ao gerar flashcards.")
        return jsonify({
            "success": False,
            "message": "Não foi possível gerar os flashcards."
        }), 503


@app.route("/api/minigame/<class_id>", methods=["GET"])
def get_minigame(class_id):

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Não autenticado"
        }), 401

    try:
        topics_queue = session.get("topics_queue", [])

        doubt_topics = [
            topic["name"] if isinstance(topic, dict) else topic
            for topic in topics_queue
        ]

        class_data = get_tutor().memory.get_class_by_id(class_id) or {}
        class_title = class_data.get("title", "Aula de Inglês")

        game_data = get_content_agent().generate_student_minigame(
            class_title,
            doubt_topics
        )

        return jsonify({
            "success": True,
            "game": game_data
        })

    except Exception:
        app.logger.exception("Erro ao gerar mini-game.")
        return jsonify({
            "success": False,
            "message": "Não foi possível gerar o mini-game."
        }), 503


# ==========================================================
# EXECUÇÃO LOCAL
# ==========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
