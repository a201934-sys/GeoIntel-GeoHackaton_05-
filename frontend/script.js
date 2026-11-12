
// =====================================
// GEOINTEL - EXPLORATION COPILOT
// Frontend Interaction
// =====================================

document.addEventListener("DOMContentLoaded", () => {

    console.log("GeoIntel interface initialized.");

    // Navigation
    const navItems = document.querySelectorAll(".nav-item");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");
        });
    });

    // Chat functionality
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");

    function addMessage(message, sender) {
        if (!chatMessages) return;

        const messageElement = document.createElement("div");
        messageElement.className = `message ${sender}`;
        messageElement.textContent = message;

        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", (event) => {
            event.preventDefault();

            const question = chatInput.value.trim();

            if (!question) return;

            addMessage(question, "user");

            chatInput.value = "";

            addMessage(
                "Demo interface: AI backend connection is pending.",
                "assistant"
            );
        });
    }

    // Suggested questions
    document.querySelectorAll("[data-question]").forEach(button => {
        button.addEventListener("click", () => {
            if (!chatInput) return;

            chatInput.value = button.dataset.question;
            chatInput.focus();
        });
    });

});
