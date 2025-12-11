/* ============================================================
   AUTO-SUGGEST AIRPORT CODES
   ============================================================ */
const AIRPORTS = ["DEL - Delhi", "DXB - Dubai", "LHR - London Heathrow",
"LAX - Los Angeles", "JFK - New York", "DOH - Doha", "SIN - Singapore",
"FRA - Frankfurt", "AMS - Amsterdam", "BOM - Mumbai"];

function enableAirportSuggest(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener("input", () => {
        let value = input.value.toUpperCase();
        let suggestions = AIRPORTS.filter(a => a.includes(value));

        let box = document.getElementById(inputId + "-suggest");
        if (!box) {
            box = document.createElement("div");
            box.id = inputId + "-suggest";
            box.className = "suggest-box";
            input.parentNode.appendChild(box);
        }

        box.innerHTML = "";
        suggestions.forEach(s => {
            let div = document.createElement("div");
            div.className = "suggest-item";
            div.innerText = s;
            div.onclick = () => {
                input.value = s.split(" - ")[0];
                box.innerHTML = "";
            };
            box.appendChild(div);
        });
    });
}

/* Enable suggestions on all pages */
enableAirportSuggest("origin");
enableAirportSuggest("destination");


/* ============================================================
   AUTO-FILL TODAY'S DATE
   ============================================================ */
window.addEventListener("load", () => {
    document.querySelectorAll('input[type="date"]').forEach(i => {
        if (!i.value) i.value = new Date().toISOString().split("T")[0];
    });
});


/* ============================================================
   REAL-TIME BOOKING HOLD COUNTDOWN
   ============================================================ */
function startCountdown(expireTime, displayId) {
    const display = document.getElementById(displayId);
    if (!display) return;

    const timer = setInterval(() => {
        let remaining = Math.floor((expireTime - Date.now()) / 1000);
       if (remaining <= 0) {
    timer.innerText = "EXPIRED";
    timer.style.color = "red";

    // Update status visually
    const statusCell = timer.parentElement.previousElementSibling;
    statusCell.innerHTML = '<span class="status status-expired">CANCELLED</span>';

    // Update action visually
    const actionCell = timer.parentElement.nextElementSibling;
    actionCell.innerHTML = '<span style="color:red;font-weight:bold;">Cancelled</span>';
}

}


/* ============================================================
   AUTO-REFRESH WORKSPACE CHAT
   ============================================================ */
function startChatAutoRefresh() {
    const box = document.getElementById("messageBox");
    if (!box) return;

    setInterval(() => {
        fetch("/workspace_data")
            .then(r => r.json())
            .then(data => {
                box.innerHTML = "";
                data.messages.forEach(m => {
                    box.innerHTML += `<div class="message"><b>${m.sender}:</b> ${m.text}</div>`;
                });
            });
    }, 3000);
}

startChatAutoRefresh();


/* ============================================================
   INTERLINE ROUTE VISUALIZER (ARROWS)
   ============================================================ */
function drawRouteLine(elementId, legs) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.innerHTML = "";
    legs.forEach((leg, i) => {
        el.innerHTML += `<span>${leg}</span>`;
        if (i < legs.length - 1) el.innerHTML += " ➝ ";
    });
}


/* ============================================================
   FORM VALIDATION (SHAKE EFFECT)
   ============================================================ */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let valid = true;
    form.querySelectorAll("input").forEach(i => {
        if (!i.value.trim()) {
            i.classList.add("input-error");
            valid = false;

            setTimeout(() => i.classList.remove("input-error"), 500);
        }
    });

    return valid;
}


/* ============================================================
   HIGHLIGHT LOW CAPACITY (< 1000 KG)
   ============================================================ */
function highlightLowCapacity() {
    document.querySelectorAll(".capacity").forEach(c => {
        let value = Number(c.dataset.cap);
        if (value < 1000) {
            c.style.color = "red";
            c.style.fontWeight = "bold";
        }
    });
}

highlightLowCapacity();


/* ============================================================
   DISABLE BUTTON WHILE PROCESSING
   ============================================================ */
function lockButton(buttonId) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    btn.disabled = true;
    btn.innerHTML = "Processing...";
}


/* ============================================================
   LIVE SEARCH FILTER (Client-side)
   ============================================================ */
function enableLiveFilter(inputId, listClass) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener("input", () => {
        const term = input.value.toLowerCase();
        document.querySelectorAll("." + listClass).forEach(item => {
            item.style.display =
                item.textContent.toLowerCase().includes(term) ? "block" : "none";
        });
    });
}


/* ============================================================
   DARK MODE TOGGLE
   ============================================================ */
function enableDarkMode() {
    const btn = document.getElementById("darkModeBtn");
    if (!btn) return;

    btn.addEventListener("click", () => {
        document.body.classList.toggle("dark");

        if (document.body.classList.contains("dark")) {
            localStorage.setItem("theme", "dark");
            btn.innerText = "Light Mode";
        } else {
            localStorage.setItem("theme", "light");
            btn.innerText = "Dark Mode";
        }
    });

    // Restore user choice
    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark");
        btn.innerText = "Light Mode";
    }
}

enableDarkMode();
