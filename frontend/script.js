
// PAGE NAVIGATION
const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page-section");
const pageTitle = document.getElementById("page-title");

navItems.forEach(item => {
    item.addEventListener("click", () => {

        navItems.forEach(nav => nav.classList.remove("active"));
        pages.forEach(page => page.classList.remove("active"));

        item.classList.add("active");

        const page = item.dataset.page;
        document.getElementById(page).classList.add("active");

        pageTitle.textContent = item.textContent.trim().replace(/^[^\w]+/, "");
    });
});


// CHAT INTERFACE
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");

function addMessage(sender, message) {

    const messageDiv = document.createElement("div");

    messageDiv.className =
        sender === "You" ? "message user" : "message assistant";

    const name = document.createElement("strong");
    name.textContent = sender;

    const text = document.createElement("p");
    text.textContent = message;

    messageDiv.appendChild(name);
    messageDiv.appendChild(text);

    chatMessages.appendChild(messageDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// SEND MESSAGE
chatForm.addEventListener("submit", function(event) {

    event.preventDefault();

    const question = chatInput.value.trim();

    if (!question) return;

    addMessage("You", question);

    chatInput.value = "";

    addMessage(
        "GeoIntel AI",
        "Your question has been received. AI backend integration with Gemma 4 is pending."
    );

});


// SUGGESTED QUESTIONS
document.querySelectorAll(".suggestions button").forEach(button => {

    button.addEventListener("click", () => {

        chatInput.value = button.dataset.question;

        chatInput.focus();

    });

});


// INITIALIZATION
console.log("GeoIntel frontend initialized successfully.");

