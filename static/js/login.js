document.addEventListener("DOMContentLoaded", () => {
    const usernameInput = document.getElementById("username");
    const loginForm = document.querySelector("form");
    const submitBtn = document.querySelector(".btn-submit");

    // 1. Coloca o cursor automaticamente no campo de Usuário ao abrir a página
    if (usernameInput) {
        usernameInput.focus();

        // 2. Remove espaços extras sem querer no início ou fim do usuário
        usernameInput.addEventListener("blur", () => {
            usernameInput.value = usernameInput.value.trim();
        });
    }

    // 3. Evita que o usuário clique duas vezes no botão de entrar enviando a requisição duplicada
    if (loginForm && submitBtn) {
        loginForm.addEventListener("submit", () => {
            submitBtn.disabled = true;
            submitBtn.style.opacity = "0.7";
            submitBtn.innerText = "Entrando...";
        });
    }
});