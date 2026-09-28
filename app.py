import os
import json
import urllib.parse
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv

from agent.core_2 import AgenticTutor
from agent.content_agent import ContentAgent

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "comum_secret_key_123")

# ==========================================================
# 🔑 INICIALIZAÇÃO DOS AGENTES E BANCO SQLITE
# ==========================================================
tutor = AgenticTutor()
content_agent = ContentAgent(memory=tutor.memory)


# ==========================================================
# 📍 ROTAS DE NAVEGAÇÃO (PÁGINAS)
# ==========================================================

@app.route("/")
def index():
    """1. Landing Page institucional com a proposta do COMUM Agentic Tutor."""
    return render_template("index2.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """2. Tela de Login e criação automática do perfil no SQLite."""
    if request.method == "POST":
        role = request.form.get("role", "aluno")
        user_name = request.form.get("username") or request.form.get("user_name", "Aluno")

        session["user_id"] = user_name
        session["user_name"] = user_name
        session["user_role"] = role

        tutor.memory.set_user_profile(user_name, level="A1", module="Vocabulary")

        if role == "professor":
            return redirect(url_for("teacher_dashboard"))
        return redirect(url_for("select_cards"))

    return render_template("login.html")


@app.route("/select-cards")
def select_cards():
    """3. Tela de seleção de aulas/cards consultando o SQLite."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    teacher_id = "prof_01"
    raw_classes = tutor.memory.list_classes(teacher_id=teacher_id) or []
    classes = []

    for c in raw_classes:
        class_id = c.stem if hasattr(c, 'stem') else str(c)
        data = tutor.memory.get_class(class_id, teacher_id=teacher_id) or {}
        classes.append({
            "id": class_id,
            "class_id": class_id,
            "title": data.get("title", f"Aula {class_id}"),
            "description": data.get("description", "Módulo focado no aprendizado prático."),
            "code": data.get("code", "Módulo")
        })

    if not classes:
        classes = [{
            "id": "class_01",
            "class_id": "class_01",
            "title": "Aula 01 - Expressões & Vocabulário",
            "description": "Pratique vocabulário básico e estruturas cotidianas em inglês.",
            "code": "Módulo 1"
        }]

    return render_template("select_cards.html", classes=classes)


@app.route("/teacher/dashboard")
def teacher_dashboard():
    """4. Dashboard do Professor."""
    return "<h1>Área do Professor</h1><p>Acompanhamento de progresso via SQLite ativo.</p>"


@app.route("/brainstorm/<class_id>")
def brainstorm_page(class_id):
    """5. Tela da Nuvem de Palavras (Diagnóstico Inicial)."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    roadmap = content_agent.build_brainstorm_roadmap(user_id=user_id, teacher_id="prof_01", class_id=class_id)
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

    for d in duvidas:
        content_agent.record_diagnosis(user_id=user_id, class_id=class_id, topic=d, status="partial")
    for dom in dominados:
        content_agent.record_diagnosis(user_id=user_id, class_id=class_id, topic=dom, status="mastered")

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
    class_id = data.get("class_id", "class_01")  # <--- Pega o ID da aula

    if not user_message:
        return jsonify({"status": "error", "message": "Mensagem vazia"}), 400

    try:
        # Recupera as dúvidas da sessão
        topics_queue = session.get("topics_queue", [])

        # Passa class_id e topics_queue para o tutor
        ai_response = tutor.respond(
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


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)