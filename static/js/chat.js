document.addEventListener("DOMContentLoaded", () => {
    // --------------------------------------------------
    // 1. REFERÊNCIAS DO DOM E ESTADOS GERAIS
    // --------------------------------------------------
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("typing-indicator");
    
    const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
    const closePanelBtn = document.getElementById("close-panel-btn");
    const sidePanel = document.getElementById("side-panel");
    const tabBtns = document.querySelectorAll(".tab-btn");

    // Flashcards
    const flashcardCard = document.getElementById("flashcard");
    const cardInner = document.getElementById("card-inner");
    const cardFront = document.getElementById("card-front");
    const cardBack = document.getElementById("card-back");
    const btnNextCard = document.getElementById("btn-next-card");

    // Mini-Games
    const tabGames = document.getElementById("tab-games");

    // Estados da Aplicação
    let currentCards = [];
    let currentCardIndex = 0;
    let currentGameData = null;

    const currentClassId = typeof CLASS_ID !== "undefined" ? CLASS_ID : "class_01";

    // --------------------------------------------------
    // 3. CHAT E ENVIO DE MENSAGENS
    // --------------------------------------------------
    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;

            addMessage(text, "user");
            userInput.value = "";
            showTyping(true);

            try {
                const res = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        message: text,
                        class_id: currentClassId
                    })
                });

                const data = await res.json();
                showTyping(false);

                if (res.ok && data.response) {
                    addMessage(data.response, "tutor");
                } else {
                    addMessage(data.message || "Não consegui obter a resposta no momento.", "tutor");
                }
            } catch (err) {
                showTyping(false);
                addMessage("Ops, perdi a conexão com o servidor. Tente novamente.", "tutor");
            }
        });
    }

    function addMessage(text, sender) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("message-wrapper", sender);

        const bubble = document.createElement("div");
        bubble.classList.add("message-bubble");

        const contentDiv = document.createElement("div");
        contentDiv.classList.add("bubble-content");

        if (sender === "tutor" && typeof marked !== "undefined") {
            contentDiv.innerHTML = marked.parse(text);
        } else {
            contentDiv.innerText = text;
        }

        bubble.appendChild(contentDiv);

        if (sender === "tutor") {
            const speakBtn = document.createElement("button");
            speakBtn.className = "btn-speak-msg";
            speakBtn.title = "Ouvir resposta";
            speakBtn.innerText = "🔊";
            bubble.appendChild(speakBtn);
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

    // --------------------------------------------------
    // 4. PAINEL LATERAL & ABAS
    // --------------------------------------------------
    if (toggleSidebarBtn && sidePanel) {
        toggleSidebarBtn.addEventListener("click", () => {
            sidePanel.classList.toggle("hidden");
            if (!sidePanel.classList.contains("hidden") && currentCards.length === 0) {
                loadFlashcards();
            }
        });
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

            if (tabName === "games" && !currentGameData) {
                loadMiniGame();
            }
        });
    });

    // --------------------------------------------------
    // 5. FLASHCARDS ADAPTATIVOS
    // --------------------------------------------------
    async function loadFlashcards() {
        if (!cardFront) return;
        cardFront.innerHTML = "<p>🤖 Gerando flashcards para suas dúvidas...</p>";
        if (cardBack) cardBack.innerText = "...";

        try {
            const res = await fetch(`/api/flashcards/${currentClassId}`);
            const data = await res.json();

            if (data.success && data.flashcards && data.flashcards.length > 0) {
                currentCards = data.flashcards;
                currentCardIndex = 0;
                renderCard();
            } else {
                cardFront.innerHTML = "<p>Nenhum card disponível.</p>";
            }
        } catch (err) {
            cardFront.innerHTML = "<p>Erro ao carregar flashcards.</p>";
        }
    }

    function renderCard() {
        if (cardInner) cardInner.classList.remove("flipped");
        const card = currentCards[currentCardIndex];
        if (card && cardFront && cardBack) {
            cardFront.innerHTML = `
                <p style="font-size: 1.1rem; font-weight: 600;">${card.front}</p>
                <small style="color: #fc9e4f; display:block; margin-top:12px; font-weight: 500;">
                    💡 Dica: ${card.hint || 'Clique para virar'}
                </small>
            `;
            cardBack.innerHTML = `<p style="font-size: 1.05rem; font-weight: 500;">${card.back}</p>`;
        }
    }

    if (flashcardCard && cardInner) {
        flashcardCard.addEventListener("click", () => {
            cardInner.classList.toggle("flipped");
        });
    }

    if (btnNextCard) {
        btnNextCard.addEventListener("click", () => {
            if (currentCards.length > 0) {
                currentCardIndex = (currentCardIndex + 1) % currentCards.length;
                renderCard();
            }
        });
    }

    // --------------------------------------------------
    // 6. MINI-GAMES DINÂMICOS (EVENT DELEGATION SEGURO)
    // --------------------------------------------------
    async function loadMiniGame() {
        if (!tabGames) return;
        tabGames.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #fc9e4f;">
                <p>🎲 Criando um mini-game de IA para você...</p>
            </div>
        `;

        try {
            const res = await fetch(`/api/minigame/${currentClassId}?t=${Date.now()}`);
            const data = await res.json();

            if (data.success && data.game) {
                currentGameData = data.game;
                renderMiniGame(currentGameData);
            } else {
                tabGames.innerHTML = `<p>Não foi possível carregar o mini-game.</p>`;
            }
        } catch (err) {
            tabGames.innerHTML = `<p>Erro ao carregar o mini-game.</p>`;
        }
    }

    function renderMiniGame(game) {
        if (!tabGames) return;

        let contentHtml = "";

        if (game.game_type === "avatar_quest" || game.steps) {
            contentHtml = renderAvatarQuestType(game);
        } else if (game.game_type === "quiz" || game.questions) {
            contentHtml = renderQuizType(game);
        } else if (game.game_type === "unscramble" || game.items) {
            contentHtml = renderUnscrambleType(game);
        } else if (game.game_type === "match" || game.pairs) {
            contentHtml = renderMatchType(game);
        }

        tabGames.innerHTML = `
            <div class="game-box">
                <h4 style="margin-bottom: 14px; color: #fc9e4f; font-size: 1.1rem;">🎮 ${game.game_title || 'Desafio de IA'}</h4>
                ${contentHtml}
                <button id="btn-reload-game" class="btn-game-start" style="margin-top: 16px;">
                    🔄 Gerar Novo Jogo (IA)
                </button>
            </div>
        `;

        const reloadBtn = document.getElementById("btn-reload-game");
        if (reloadBtn) {
            reloadBtn.addEventListener("click", () => {
                currentGameData = null;
                loadMiniGame();
            });
        }
    }

    // RENDERIZADORES COM DATA-ATTRIBUTES
    function renderAvatarQuestType(game) {
        let html = `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(252,158,79,0.3); border-radius: 12px; padding: 12px; margin-bottom: 15px;">
                <p style="font-size: 0.85rem; color: #aaa; margin-bottom: 10px;">📖 <strong>História:</strong> ${game.story || ''}</p>
        `;

        (game.steps || []).forEach((step, idx) => {
            html += `
                <div style="margin-top: 12px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                    <div style="display: flex; gap: 10px; align-items: flex-start; margin-bottom: 12px;">
                        <div style="font-size: 2rem; background: #2a2a3e; border-radius: 50%; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border: 2px solid #fc9e4f; flex-shrink: 0;">
                            ${step.expression || game.avatar_icon || '👨‍🚀'}
                        </div>
                        <div style="background: #1e1e2f; border: 1px solid #444; border-radius: 10px; padding: 10px; flex: 1;">
                            <strong style="color: #fc9e4f; font-size: 0.8rem; display: block; margin-bottom: 4px;">${game.avatar_name || 'Tutor'}:</strong>
                            <p style="font-size: 0.95rem; color: #fff; margin: 0;">"${step.speech}"</p>
                        </div>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 8px;">
            `;

            (step.options || []).forEach((opt, optIdx) => {
                html += `
                    <button class="quest-opt-btn" data-step="${idx}" data-opt="${optIdx}"
                            id="btn-quest-${idx}-opt${optIdx}" 
                            style="padding: 8px 12px; text-align: left; border-radius: 8px; border: 1px solid #3a3a50; background: #252538; color: #fff; cursor: pointer; font-size: 0.9rem;">
                        💬 ${opt}
                    </button>
                `;
            });

            html += `
                    </div>
                    <p id="quest-feedback-${idx}" style="margin-top: 10px; font-size: 0.85rem; display: none; padding: 8px; border-radius: 6px;"></p>
                </div>
            `;
        });

        html += `</div>`;
        return html;
    }

    function renderQuizType(game) {
        let html = '<div id="quiz-container">';
        (game.questions || []).forEach((q, idx) => {
            html += `
                <div style="margin-bottom: 16px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px;">
                    <p style="font-size: 0.9rem; margin-bottom: 10px;"><strong>Q${idx + 1}:</strong> ${q.question}</p>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
            `;
            q.options.forEach((opt, optIdx) => {
                html += `
                    <button class="quiz-opt-btn" data-q="${idx}" data-opt="${optIdx}"
                            id="btn-q${idx}-opt${optIdx}" 
                            style="padding: 8px 12px; text-align: left; border-radius: 6px; border: 1px solid #444; background: #2a2a2a; color: #fff; cursor: pointer;">
                        ${opt}
                    </button>
                `;
            });
            html += `
                    </div>
                    <p id="feedback-q${idx}" style="margin-top: 8px; font-size: 0.85rem; display: none;"></p>
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    function renderUnscrambleType(game) {
        let html = '<div id="unscramble-container">';
        (game.items || []).forEach((item, idx) => {
            html += `
                <div style="margin-bottom: 18px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px;">
                    <p style="font-size: 0.85rem; color: #aaa;">Tradução: "${item.translation}"</p>
                    <p style="font-size: 0.9rem; margin: 8px 0; font-weight: bold;">Ordene as palavras:</p>
                    
                    <div id="words-pool-${idx}" style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;">
                        ${(item.scrambled || []).map(w => `
                            <span class="unscramble-word" data-item="${idx}" data-word="${w}" style="padding: 6px 10px; background: #3a3a50; border-radius: 6px; cursor: pointer; user-select: none;">${w}</span>
                        `).join('')}
                    </div>

                    <div style="min-height: 38px; padding: 6px; background: #1a1a24; border: 1px dashed #fc9e4f; border-radius: 6px; margin-bottom: 8px;" id="answer-box-${idx}"></div>

                    <button class="unscramble-verify-btn" data-item="${idx}" style="width: 100%; padding: 8px; background: #2ed573; color: #000; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">Verificar Frase</button>
                    <p id="unscramble-feedback-${idx}" style="margin-top: 8px; font-size: 0.85rem; display: none;"></p>
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    function renderMatchType(game) {
        let html = '<div style="margin-bottom: 15px;"><p style="font-size: 0.85rem; color: #aaa;">Selecione os pares equivalentes:</p></div>';
        html += '<div style="display: flex; flex-direction: column; gap: 8px;">';
        
        (game.pairs || []).forEach((p, idx) => {
            html += `
                <div style="display: flex; gap: 8px; justify-content: space-between;">
                    <button class="match-opt-btn" data-pair="${idx}" data-lang="en" id="match-en-${idx}" style="flex: 1; padding: 8px; background: #2a2a3c; border: 1px solid #fc9e4f; border-radius: 6px; color: #fff; cursor: pointer;">${p.english}</button>
                    <button class="match-opt-btn" data-pair="${idx}" data-lang="pt" id="match-pt-${idx}" style="flex: 1; padding: 8px; background: #2a2a3c; border: 1px solid #2ed573; border-radius: 6px; color: #fff; cursor: pointer;">${p.portuguese}</button>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }

    // --------------------------------------------------
    // 7. LISTENERS DE EVENTO PARA OS MINI-GAMES
    // --------------------------------------------------
    if (tabGames) {
        tabGames.addEventListener("click", (e) => {
            // A. Clique em Opção do Avatar Quest
            const questBtn = e.target.closest(".quest-opt-btn");
            if (questBtn) {
                const stepIdx = parseInt(questBtn.dataset.step, 10);
                const optIdx = parseInt(questBtn.dataset.opt, 10);
                handleAvatarChoice(stepIdx, optIdx);
                return;
            }

            // B. Clique em Opção do Quiz
            const quizBtn = e.target.closest(".quiz-opt-btn");
            if (quizBtn) {
                const qIdx = parseInt(quizBtn.dataset.q, 10);
                const optIdx = parseInt(quizBtn.dataset.opt, 10);
                handleQuizChoice(qIdx, optIdx);
                return;
            }

            // C. Clique em Palavra do Unscramble
            const wordSpan = e.target.closest(".unscramble-word");
            if (wordSpan) {
                const itemIdx = parseInt(wordSpan.dataset.item, 10);
                const word = wordSpan.dataset.word;
                handleWordClick(itemIdx, word, wordSpan);
                return;
            }

            // D. Clique em Verificar Unscramble
            const verifyBtn = e.target.closest(".unscramble-verify-btn");
            if (verifyBtn) {
                const itemIdx = parseInt(verifyBtn.dataset.item, 10);
                handleUnscrambleVerify(itemIdx);
                return;
            }

            // E. Clique nos Pares do Match
            const matchBtn = e.target.closest(".match-opt-btn");
            if (matchBtn) {
                const pairIdx = parseInt(matchBtn.dataset.pair, 10);
                handleMatchClick(pairIdx);
                return;
            }
        });
    }

    function handleAvatarChoice(stepIdx, selectedOpt) {
        if (!currentGameData || !currentGameData.steps) return;
        const step = currentGameData.steps[stepIdx];
        if (!step) return;

        const feedbackEl = document.getElementById(`quest-feedback-${stepIdx}`);
        const opts = tabGames.querySelectorAll(`.quest-opt-btn[data-step="${stepIdx}"]`);
        opts.forEach(btn => btn.disabled = true);

        const correctOpt = parseInt(step.answer_index, 10);
        const feedbackText = step.feedback || (selectedOpt === correctOpt ? "Resposta correta!" : "Tente novamente.");

        const selectedBtn = tabGames.querySelector(`.quest-opt-btn[data-step="${stepIdx}"][data-opt="${selectedOpt}"]`);
        const correctBtn = tabGames.querySelector(`.quest-opt-btn[data-step="${stepIdx}"][data-opt="${correctOpt}"]`);

        if (selectedOpt === correctOpt) {
            if (selectedBtn) {
                selectedBtn.style.background = "#2ed573";
                selectedBtn.style.color = "#000";
            }
            if (feedbackEl) {
                feedbackEl.style.background = "rgba(46, 213, 115, 0.15)";
                feedbackEl.style.color = "#2ed573";
                feedbackEl.innerText = `🎉 ${feedbackText}`;
            }
        } else {
            if (selectedBtn) {
                selectedBtn.style.background = "#ff4757";
                selectedBtn.style.color = "#fff";
            }
            if (correctBtn) {
                correctBtn.style.background = "#2ed573";
                correctBtn.style.color = "#000";
            }
            if (feedbackEl) {
                feedbackEl.style.background = "rgba(255, 71, 87, 0.15)";
                feedbackEl.style.color = "#ff4757";
                feedbackEl.innerText = `💡 ${feedbackText}`;
            }
        }
        if (feedbackEl) feedbackEl.style.display = "block";
    }

    function handleQuizChoice(qIdx, selectedOpt) {
        if (!currentGameData || !currentGameData.questions) return;
        const q = currentGameData.questions[qIdx];
        if (!q) return;

        const feedbackEl = document.getElementById(`feedback-q${qIdx}`);
        const opts = tabGames.querySelectorAll(`.quiz-opt-btn[data-q="${qIdx}"]`);
        opts.forEach(btn => btn.disabled = true);

        const correctOpt = parseInt(q.answer_index, 10);
        const explanation = q.explanation || "";

        const selectedBtn = tabGames.querySelector(`.quiz-opt-btn[data-q="${qIdx}"][data-opt="${selectedOpt}"]`);
        const correctBtn = tabGames.querySelector(`.quiz-opt-btn[data-q="${qIdx}"][data-opt="${correctOpt}"]`);

        if (selectedOpt === correctOpt) {
            if (selectedBtn) selectedBtn.style.background = "#2ed573";
            if (feedbackEl) {
                feedbackEl.style.color = "#2ed573";
                feedbackEl.innerText = `✅ Correto! ${explanation}`;
            }
        } else {
            if (selectedBtn) selectedBtn.style.background = "#ff4757";
            if (correctBtn) correctBtn.style.background = "#2ed573";
            if (feedbackEl) {
                feedbackEl.style.color = "#ff4757";
                feedbackEl.innerText = `❌ Incorreto. ${explanation}`;
            }
        }
        if (feedbackEl) feedbackEl.style.display = "block";
    }

    function handleWordClick(itemIdx, word, wordSpan) {
        const box = document.getElementById(`answer-box-${itemIdx}`);
        if (box) {
            box.innerText = (box.innerText + " " + word).trim();
        }
        wordSpan.style.opacity = "0.3";
        wordSpan.style.pointerEvents = "none";
    }

    function handleUnscrambleVerify(itemIdx) {
        if (!currentGameData || !currentGameData.items) return;
        const item = currentGameData.items[itemIdx];
        if (!item) return;

        const box = document.getElementById(`answer-box-${itemIdx}`);
        const feedback = document.getElementById(`unscramble-feedback-${itemIdx}`);
        if (!box || !feedback) return;

        const userSentence = box.innerText.trim().toLowerCase();
        const correctSentence = (item.correct || "").trim().toLowerCase();

        if (userSentence === correctSentence) {
            feedback.style.color = "#2ed573";
            feedback.innerText = "✅ Perfeito! Frase montada corretamente.";
        } else {
            feedback.style.color = "#ff4757";
            feedback.innerText = `❌ Quase! A frase correta é: "${item.correct}"`;
        }
        feedback.style.display = "block";
    }

    function handleMatchClick(pairIdx) {
        const btnEn = document.getElementById(`match-en-${pairIdx}`);
        const btnPt = document.getElementById(`match-pt-${pairIdx}`);
        if (btnEn && btnPt) {
            btnEn.style.background = "#2ed573";
            btnEn.style.color = "#000";
            btnPt.style.background = "#2ed573";
            btnPt.style.color = "#000";
        }
    }
});