document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("typing-indicator");
    
    const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
    const closePanelBtn = document.getElementById("close-panel-btn");
    const sidePanel = document.getElementById("side-panel");
    const tabBtns = document.querySelectorAll(".tab-btn");

    // --- FUNÇÃO DE VOZ (TEXT-TO-SPEECH) ---
    function speakText(text) {
        if (!('speechSynthesis' in window)) return;

        // Para qualquer fala anterior que ainda esteja tocando
        window.speechSynthesis.cancel();

        // Remove símbolos de Markdown (**, *, #, `, etc.) para a voz ler apenas o texto puro
        const cleanText = text.replace(/[*#_~`]/g, '').trim();

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-US'; // Define sotaque para Inglês americano
        utterance.rate = 0.95;    // Velocidade levemente ajustada para fácil compreensão

        window.speechSynthesis.speak(utterance);
    }

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Exibe a mensagem do usuário imediatamente
        addMessage(text, "user");
        userInput.value = "";
        showTyping(true);

        try {
            // 2. Faz a requisição enviando a mensagem
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    class_id: typeof CLASS_ID !== "undefined" ? CLASS_ID : "class_01"
                })
            });

            const data = await res.json();
            showTyping(false);

            if (res.ok && data.response) {
                addMessage(data.response, "tutor");
                
                // 🔊 3. Toca a voz automaticamente assim que a mensagem do tutor chega
                speakText(data.response);

            } else {
                console.error("Erro retornado do servidor:", data);
                addMessage(data.message || "Não consegui obter a resposta no momento.", "tutor");
            }
        } catch (err) {
            console.error("Erro na comunicação:", err);
            showTyping(false);
            addMessage("Ops, perdi a conexão com o servidor. Tente novamente.", "tutor");
        }
    });

    function addMessage(text, sender) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("message-wrapper", sender);

        const bubble = document.createElement("div");
        bubble.classList.add("message-bubble");

        // Renderiza Markdown para o tutor e texto puro para o usuário
        if (sender === "tutor" && typeof marked !== "undefined") {
            bubble.innerHTML = marked.parse(text);
        } else {
            bubble.innerText = text;
        }

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping(show) {
        if (show) {
            typingIndicator.classList.remove("hidden");
        } else {
            typingIndicator.classList.add("hidden");
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Controle do Painel Lateral
    if (toggleSidebarBtn && sidePanel) {
        toggleSidebarBtn.addEventListener("click", () => sidePanel.classList.toggle("hidden"));
    }
    if (closePanelBtn && sidePanel) {
        closePanelBtn.addEventListener("click", () => sidePanel.classList.add("hidden"));
    }

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const tabName = btn.dataset.tab;
            document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
            const targetTab = document.getElementById(`tab-${tabName}`);
            if (targetTab) targetTab.classList.remove("hidden");
        });
    });
});