// Variable to manage animation frame loop globally
let animationFrameId = null;

function inicializarNuvem() {
    const container = document.getElementById("cloudContainer");
    const selectedCountEl = document.getElementById("selectedCount");
    const selectedTopics = new Set();

    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }

    if (container) {
        container.innerHTML = "";
    } else {
        return;
    }

    if (selectedCountEl) {
        selectedCountEl.innerText = "0";
    }

    if (typeof TOPICOS_AULA === "undefined" || !TOPICOS_AULA || TOPICOS_AULA.length === 0) {
        container.innerHTML = `<p style="text-align:center; padding-top:100px; color: var(--gold, #EDD382);">Nenhum tópico encontrado para esta aula.</p>`;
        return;
    }

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 400;
    const tags = [];

    TOPICOS_AULA.forEach((item) => {
        const topicName = typeof item === 'string' ? item : (item.topic || item.name || "Tópico");

        const el = document.createElement("div");
        el.classList.add("word-tag");
        el.innerText = topicName;

        let x = Math.random() * (width - 180) + 20;
        let y = Math.random() * (height - 60) + 20;

        let vx = (Math.random() - 0.5) * 0.6;
        let vy = (Math.random() - 0.5) * 0.6;

        let isHovered = false;

        container.appendChild(el);

        const tagObj = { el, x, y, vx, vy, topicName, originalItem: item, getHover: () => isHovered };
        tags.push(tagObj);

        el.addEventListener("mouseenter", () => { isHovered = true; });
        el.addEventListener("mouseleave", () => { isHovered = false; });

        el.addEventListener("click", () => {
            if (selectedTopics.has(topicName)) {
                selectedTopics.delete(topicName);
                el.classList.remove("selected");
                el.innerText = topicName;
            } else {
                selectedTopics.add(topicName);
                el.classList.add("selected");
                el.innerText = `✓ ${topicName}`;
            }
            if (selectedCountEl) selectedCountEl.innerText = selectedTopics.size;
        });
    });

    function animate() {
        const boundsWidth = container.clientWidth;
        const boundsHeight = container.clientHeight;

        tags.forEach(tag => {
            if (!tag.getHover()) {
                tag.x += tag.vx;
                tag.y += tag.vy;

                const elWidth = tag.el.offsetWidth;
                const elHeight = tag.el.offsetHeight;

                if (tag.x <= 10 || tag.x + elWidth >= boundsWidth - 10) {
                    tag.vx *= -1;
                }
                if (tag.y <= 10 || tag.y + elHeight >= boundsHeight - 10) {
                    tag.vy *= -1;
                }
            }

            tag.el.style.transform = `translate(${tag.x}px, ${tag.y}px)`;
        });

        animationFrameId = requestAnimationFrame(animate);
    }

    animate();
}

document.addEventListener("DOMContentLoaded", inicializarNuvem);
window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
        inicializarNuvem();
    }
});

// Ação de Envio sincronizada com a sessão e SQLite do Flask
function enviarSelecao() {
    // 1. Coleta apenas os tópicos marcados como dúvida
    const duvidas = Array.from(document.querySelectorAll('.word-tag.selected'))
                         .map(el => el.innerText.replace('✓ ', '').trim());

    // 2. Mapeia a lista completa de tópicos para descobrir os dominados
    const todosOsTopicos = (typeof TOPICOS_AULA !== 'undefined') 
        ? TOPICOS_AULA.map(t => typeof t === 'string' ? t : (t.topic || t.name))
        : [];

    const dominados = todosOsTopicos.filter(t => !duvidas.includes(t));

    const btnConfirm = document.getElementById("btnConfirm");
    btnConfirm.innerText = "Salvando...";
    btnConfirm.disabled = true;

    // Envia sem user_id hardcoded (Flask obtém via session)
    fetch("/api/diagnostico", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            class_id: typeof CLASS_ID !== 'undefined' ? CLASS_ID : "class_01",
            duvidas: duvidas,
            dominados: dominados
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } else {
            alert("❌ Erro ao salvar diagnóstico: " + (data.message || "Tente novamente."));
        }
    })
    .catch(error => {
        console.error("Erro no envio:", error);
        alert("❌ Erro de conexão com o servidor.");
    })
    .finally(() => {
        btnConfirm.innerText = "Confirmar Diagnóstico 🚀";
        btnConfirm.disabled = false;
    });
}