document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector(".search-input");
    const toggleButtons = Array.from(document.querySelectorAll(".btn-toggle"));
    const rows = Array.from(document.querySelectorAll(".survey-row"));

    let searchQuery = "";
    let filterMode =
        document.querySelector(".btn-toggle.active")?.dataset.filter || "active";

    const normalize = (value) => (value || "").toLowerCase().trim();

    const matchesSearch = (row) => {
        if (!searchQuery) {
            return true;
        }
        const searchable = normalize(row.dataset.searchTerm);
        return searchable.includes(searchQuery);
    };

    const matchesToggle = (row) => {
        if (filterMode === "all") {
            return true;
        }
        return row.dataset.isActive === "true";
    };

    const applyFilters = () => {
        rows.forEach((row) => {
            const visible = matchesSearch(row) && matchesToggle(row);
            row.hidden = !visible;
        });
    };

    if (searchInput) {
        searchInput.addEventListener("input", (event) => {
            searchQuery = normalize(event.target.value);
            applyFilters();
        });
    }

    if (toggleButtons.length > 0) {
        toggleButtons.forEach((button) => {
            button.addEventListener("click", () => {
                filterMode = button.dataset.filter || "active";

                toggleButtons.forEach((btn) => btn.classList.remove("active"));
                button.classList.add("active");

                applyFilters();
            });
        });
    }

    const copyWithFallback = async (value) => {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
            return;
        }

        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    };

    const showCopyFeedback = (button, message) => {
        const feedback = message || "Copied";
        const originalTitle = button.dataset.originalTitle || button.getAttribute("title") || "";

        if (!button.dataset.originalTitle) {
            button.dataset.originalTitle = originalTitle;
        }

        const previousTimeout = Number(button.dataset.copyTimeoutId || "0");
        if (previousTimeout) {
            window.clearTimeout(previousTimeout);
        }

        button.classList.add("is-copied");
        button.dataset.feedback = feedback;
        button.setAttribute("title", feedback);
        button.setAttribute("aria-label", feedback);

        const timeoutId = window.setTimeout(() => {
            button.classList.remove("is-copied");
            button.removeAttribute("data-feedback");
            button.setAttribute("title", button.dataset.originalTitle || "");
            button.removeAttribute("aria-label");
            button.dataset.copyTimeoutId = "";
        }, 2000);

        button.dataset.copyTimeoutId = String(timeoutId);
    };

    document.addEventListener("click", async (event) => {
        const copyButton = event.target.closest(".btn-copy-id");
        if (!copyButton) {
            return;
        }

        const surveyId = copyButton.dataset.surveyId || "";
        const copiedMessage = copyButton.dataset.msgCopied || "Copied";
        if (!surveyId) {
            return;
        }

        try {
            await copyWithFallback(surveyId);
            showCopyFeedback(copyButton, copiedMessage);
        } catch (error) {
            console.error("Failed to copy survey id:", error);
        }
    });

    applyFilters();
});
