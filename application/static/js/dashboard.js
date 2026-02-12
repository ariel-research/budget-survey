document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector(".master-table");
    const tbody = table?.querySelector("tbody");
    const searchInput = document.querySelector(".search-input");
    const toggleButtons = Array.from(document.querySelectorAll(".btn-toggle"));
    const sortableHeaders = Array.from(
        table?.querySelectorAll("th.sortable") || []
    );

    let searchQuery = "";
    let filterMode =
        document.querySelector(".btn-toggle.active")?.dataset.filter || "active";
    let sortKey = null;
    let sortDirection = "asc";

    const numericSortKeys = new Set(["id", "status", "dim", "vol"]);

    const normalize = (value) => String(value || "").toLowerCase().trim();
    const getRows = () => Array.from(tbody?.querySelectorAll(".survey-row") || []);

    const getSortValue = (row, key) => {
        const datasetKey = `val${key.charAt(0).toUpperCase()}${key.slice(1)}`;
        const raw = row.dataset[datasetKey] || "";

        if (numericSortKeys.has(key)) {
            const asNumber = Number(raw);
            return Number.isNaN(asNumber) ? 0 : asNumber;
        }

        return normalize(raw);
    };

    const matchesSearch = (row) => {
        if (!searchQuery) {
            return true;
        }
        return normalize(row.dataset.searchTerm).includes(searchQuery);
    };

    const matchesToggle = (row) => {
        if (filterMode === "all") {
            return true;
        }
        return row.dataset.isActive === "true";
    };

    const applyFilters = () => {
        getRows().forEach((row) => {
            row.hidden = !(matchesSearch(row) && matchesToggle(row));
        });
    };

    const updateSortHeaderState = () => {
        sortableHeaders.forEach((header) => {
            const state =
                header.dataset.sortKey === sortKey ? sortDirection : "none";
            header.dataset.sortState = state;
            if (state === "asc") {
                header.setAttribute("aria-sort", "ascending");
            } else if (state === "desc") {
                header.setAttribute("aria-sort", "descending");
            } else {
                header.setAttribute("aria-sort", "none");
            }
        });
    };

    const handleSort = (columnKey) => {
        if (!tbody || !columnKey) {
            return;
        }

        if (sortKey === columnKey) {
            sortDirection = sortDirection === "asc" ? "desc" : "asc";
        } else {
            sortKey = columnKey;
            sortDirection = "asc";
        }

        const direction = sortDirection === "asc" ? 1 : -1;
        const sortedRows = getRows().sort((rowA, rowB) => {
            const valueA = getSortValue(rowA, columnKey);
            const valueB = getSortValue(rowB, columnKey);

            if (typeof valueA === "number" && typeof valueB === "number") {
                return (valueA - valueB) * direction;
            }

            return valueA.localeCompare(valueB, undefined, {
                numeric: true,
                sensitivity: "base",
            }) * direction;
        });

        sortedRows.forEach((row) => tbody.appendChild(row));
        updateSortHeaderState();
        applyFilters();
    };

    if (searchInput) {
        searchInput.addEventListener("input", (event) => {
            searchQuery = normalize(event.target.value);
            applyFilters();
        });
    }

    toggleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            filterMode = button.dataset.filter || "active";

            toggleButtons.forEach((btn) => btn.classList.remove("active"));
            button.classList.add("active");

            applyFilters();
        });
    });

    sortableHeaders.forEach((header) => {
        header.addEventListener("click", () => {
            handleSort(header.dataset.sortKey);
        });
    });

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
        const originalTitle =
            button.dataset.originalTitle || button.getAttribute("title") || "";

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

    updateSortHeaderState();
    applyFilters();
});
