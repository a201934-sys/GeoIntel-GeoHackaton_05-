
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


// =====================================
// GEOINTEL AI VISUALIZATION ENGINE
// =====================================

const vizPanel = document.getElementById("visualization-panel");
const vizChart = document.getElementById("visualization-chart");
const vizTitle = document.getElementById("visualization-title");
const vizDescription = document.getElementById("visualization-description");

const vizTabs = document.querySelectorAll(".viz-tab");

let currentVisualization = "seismic";

// Generate visualization based on question
function generateVisualization(question) {

    const q = question.toLowerCase();

    let type = "seismic";

    if (q.includes("well log") || q.includes("gamma ray") || q.includes("resistivity")) {
        type = "welllog";
    } 
    else if (q.includes("sand") || q.includes("probability") || q.includes("vsh")) {
        type = "probability";
    } 
    else if (q.includes("cross-section") || q.includes("cross section") || q.includes("fault") || q.includes("trap")) {
        type = "crosssection";
    }

    vizPanel.hidden = false;
    displayVisualization(type);
}

// Display selected visualization
function displayVisualization(type) {

    currentVisualization = type;

    vizTabs.forEach(tab => {
        tab.classList.toggle("active", tab.dataset.viz === type);
    });

    const visualizations = {

        seismic: {
            title: "Seismic Reflection Model",
            description: "Illustrative subsurface seismic reflection patterns",
            html: `
                <svg viewBox="0 0 700 320" width="100%" role="img" aria-label="Illustrative seismic reflection model">
                    <defs>
                        <linearGradient id="seisbg" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#142b43"/>
                            <stop offset="100%" stop-color="#071321"/>
                        </linearGradient>
                    </defs>
                    <rect width="700" height="320" fill="url(#seisbg)" rx="8"/>
                    ${Array.from({length: 10}, (_, i) => `
                        <path d="M0 ${55+i*25} 
                        Q100 ${35+i*25} 200 ${55+i*25}
                        T400 ${55+i*25} T700 ${55+i*25}"
                        fill="none" stroke="${i%2===0 ? '#43d9cb':'#e8edf5'}"
                        stroke-width="2" opacity=".8"/>
                    `).join("")}
                    <path d="M350 70 L390 280" stroke="#ff9b54" stroke-width="3" stroke-dasharray="7 5"/>
                    <text x="20" y="25" fill="white" font-size="13">SEISMIC SECTION</text>
                    <text x="410" y="285" fill="#ffbd80" font-size="13">Fault</text>
                </svg>
            `
        },

        welllog: {
            title: "Petrophysical Well Log",
            description: "Illustrative gamma ray, resistivity and porosity curves",
            html: `
                <svg viewBox="0 0 700 320" width="100%" role="img" aria-label="Illustrative well log curves">
                    <rect width="700" height="320" fill="#101f30" rx="8"/>
                    ${[0,1,2].map(i => `
                        <rect x="${20+i*225}" y="35" width="205" height="245"
                        fill="#172b40" stroke="#52657a"/>
                    `).join("")}
                    <g fill="white" font-size="13">
                        <text x="35" y="25">Gamma Ray</text>
                        <text x="260" y="25">Resistivity</text>
                        <text x="485" y="25">Porosity</text>
                    </g>
                    <path d="M40 60 L100 90 L70 130 L150 170 L80 220 L120 270"
                    fill="none" stroke="#42d8c6" stroke-width="3"/>
                    <path d="M260 60 L390 90 L320 130 L420 170 L350 220 L390 270"
                    fill="none" stroke="#f2b84b" stroke-width="3"/>
                    <path d="M480 60 L550 90 L520 130 L610 170 L540 220 L580 270"
                    fill="none" stroke="#ef8b9e" stroke-width="3"/>
                    <g stroke="#64788c" stroke-dasharray="3 5">
                        ${[100,150,200,250].map(y=>`<line x1="20" y1="${y}" x2="680" y2="${y}"/>`).join("")}
                    </g>
                </svg>
            `
        },

        probability: {
            title: "Sand Probability Distribution",
            description: "Illustrative reservoir sand probability heatmap",
            html: `
                <svg viewBox="0 0 700 320" width="100%" role="img" aria-label="Illustrative sand probability heatmap">
                    <rect width="700" height="320" fill="#101f30" rx="8"/>
                    ${Array.from({length: 8},(_,r)=>
                        Array.from({length: 12},(_,c)=>{
                            const value = Math.max(0,Math.min(1,
                                0.2+0.65*Math.exp(-((c-7)**2+(r-3)**2)/12)
                            ));
                            const color = value > .7 ? "#35d6a0" :
                                          value > .5 ? "#e5c34d" :
                                          value > .3 ? "#e88b50" : "#304c68";
                            return `<rect x="${25+c*54}" y="${35+r*32}"
                                width="50" height="28" rx="3"
                                fill="${color}"/>`;
                        }).join("")
                    ).join("")}
                    <text x="25" y="18" fill="white" font-size="13">SAND PROBABILITY</text>
                    <text x="25" y="310" fill="#35d6a0" font-size="12">High probability</text>
                    <text x="570" y="310" fill="#8da0b8" font-size="12">Low probability</text>
                </svg>
            `
        },

        crosssection: {
            title: "Geological Cross-section",
            description: "Illustrative reservoir architecture and structural traps",
            html: `
                <svg viewBox="0 0 700 320" width="100%" role="img" aria-label="Illustrative geological cross section">
                    <rect width="700" height="320" fill="#101f30" rx="8"/>
                    <path d="M0 90 Q150 60 300 100 T700 85 L700 320 L0 320Z"
                        fill="#8c7454"/>
                    <path d="M0 150 Q150 120 300 160 T700 140 L700 320 L0 320Z"
                        fill="#c49b64"/>
                    <path d="M0 205 Q180 180 340 215 T700 195 L700 320 L0 320Z"
                        fill="#d4bd80"/>
                    <path d="M0 260 Q150 230 300 265 T700 250 L700 320 L0 320Z"
                        fill="#526b83"/>
                    <path d="M330 90 L390 280" stroke="#ff765f"
                        stroke-width="4" stroke-dasharray="8 5"/>
                    <path d="M220 160 Q310 115 420 160 Q310 195 220 160Z"
                        fill="#35d6a0" opacity=".85"/>
                    <text x="40" y="125" fill="white" font-size="13">Overburden</text>
                    <text x="440" y="170" fill="#102a35" font-size="13">Reservoir</text>
                    <text x="410" y="275" fill="white" font-size="13">Basement</text>
                    <text x="395" y="100" fill="#ff9b80" font-size="13">Fault</text>
                </svg>
            `
        }
    };

    const selected = visualizations[type];

    vizTitle.textContent = selected.title;
    vizDescription.textContent = selected.description;
    vizChart.innerHTML = selected.html;
}

// Visualization tab interaction
vizTabs.forEach(tab => {

    tab.addEventListener("click", () => {
        displayVisualization(tab.dataset.viz);
    });

});

// Detect submitted geological questions
chatForm.addEventListener("submit", function() {

    const question = chatInput.value.trim();

    if (!question) return;

    generateVisualization(question);

}, true);

console.log("GeoIntel AI Visualization initialized.");


