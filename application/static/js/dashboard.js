document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector(".master-table");
    const tbody = table?.querySelector("tbody");
    const searchInput = document.querySelector(".search-input");
    const strategySelect = document.getElementById("filterStrategy");
    const storySelect = document.getElementById("filterStory");
    const dimSelect = document.getElementById("filterDim");
    const resetBtn = document.getElementById("resetFilters");
    const clearFiltersBtn = document.getElementById("clearFiltersBtn");
    const noResultsRow = document.getElementById("noResultsRow");
    const toggleButtons = Array.from(document.querySelectorAll(".btn-toggle"));
    const sortableHeaders = Array.from(
        table?.querySelectorAll("th.sortable") || []
    );

    let searchQuery = "";
    let filterMode =
        document.querySelector(".btn-toggle.active")?.dataset.filter || "active";
    let selectedStrategy = "all";
    let selectedStory = "all";
    let selectedDim = "all";
    let sortKey = null;
    let sortDirection = "asc";

    const numericSortKeys = new Set(["id", "status", "dim", "vol"]);

    const normalize = (value) => String(value || "").toLowerCase().trim();
    const getRows = () => Array.from(tbody?.querySelectorAll(".survey-row") || []);
    
    const formatDimLabel = (rawValue) => {
        const value = String(rawValue || "").trim();
        const asNumber = Number(value);

        if (!Number.isNaN(asNumber) && asNumber > 0) {
            return `${asNumber}D`;
        }
        return "N/A";
    };

    const populateFilters = () => {
        const rows = getRows();
        const strategyValues = new Set();
        const storyValues = new Set();
        const dimValues = new Set();

        rows.forEach((row) => {
            const strategyValue = String(row.dataset.valStrategy || "").trim();
            const storyValue = String(row.dataset.valStory || "").trim();
            const dimValue = String(row.dataset.valDim || "").trim();

            if (strategyValue) strategyValues.add(strategyValue);
            if (storyValue) storyValues.add(storyValue);
            if (dimValue) dimValues.add(dimValue);
        });

        const setupSelect = (select, values, allLabel, formatter = (v) => v) => {
            if (!select) return;
            const current = select.value;
            select.innerHTML = "";
            select.appendChild(new Option(allLabel, "all"));

            Array.from(values)
                .sort((a, b) => {
                    if (select === dimSelect) return Number(a) - Number(b);
                    return a.localeCompare(b, undefined, {
                        sensitivity: "base",
                        numeric: true,
                    });
                })
                .forEach((value) => {
                    select.appendChild(new Option(formatter(value), value));
                });
            
            if (Array.from(values).includes(current)) {
                select.value = current;
            } else {
                select.value = "all";
            }
        };

        setupSelect(strategySelect, strategyValues, strategySelect?.dataset.allLabel || "All Strategies");
        setupSelect(storySelect, storyValues, storySelect?.dataset.allLabel || "All Stories");
        setupSelect(dimSelect, dimValues, dimSelect?.dataset.allLabel || "All Dims", formatDimLabel);
    };

    const getSortValue = (row, key) => {
        const datasetKey = `val${key.charAt(0).toUpperCase()}${key.slice(1)}`;
        const raw = row.dataset[datasetKey] || "";

        if (numericSortKeys.has(key)) {
            const asNumber = Number(raw);
            return Number.isNaN(asNumber) ? 0 : asNumber;
        }

        return normalize(raw);
    };

    const applyFilters = () => {
        let visibleCount = 0;
        const rows = getRows();
        
        rows.forEach((row) => {
            const matchesSearch = !searchQuery || normalize(row.dataset.searchTerm).includes(searchQuery);
            const matchesToggle = filterMode === "all" || row.dataset.isActive === "true";
            const matchesStrategy = selectedStrategy === "all" || row.dataset.valStrategy === selectedStrategy;
            const matchesStory = selectedStory === "all" || row.dataset.valStory === selectedStory;
            const matchesDim = selectedDim === "all" || row.dataset.valDim === selectedDim;

            const isVisible = matchesSearch && matchesToggle && matchesStrategy && matchesStory && matchesDim;
            row.hidden = !isVisible;
            if (isVisible) visibleCount++;
        });

        if (noResultsRow) {
            noResultsRow.hidden = visibleCount > 0;
        }
    };

    const resetAllFilters = () => {
        searchQuery = "";
        if (searchInput) searchInput.value = "";
        
        selectedStrategy = "all";
        if (strategySelect) strategySelect.value = "all";
        
        selectedStory = "all";
        if (storySelect) storySelect.value = "all";
        
        selectedDim = "all";
        if (dimSelect) dimSelect.value = "all";

        filterMode = "active";
        toggleButtons.forEach(btn => {
            btn.classList.toggle("active", btn.dataset.filter === "active");
        });

        applyFilters();
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
        if (!tbody || !columnKey) return;

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

            return String(valueA).localeCompare(String(valueB), undefined, {
                numeric: true,
                sensitivity: "base",
            }) * direction;
        });

        sortedRows.forEach((row) => tbody.appendChild(row));
        updateSortHeaderState();
        applyFilters();
    };

    // Event Listeners
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            searchQuery = normalize(e.target.value);
            applyFilters();
        });
    }

    if (strategySelect) {
        strategySelect.addEventListener("change", (e) => {
            selectedStrategy = e.target.value;
            applyFilters();
        });
    }

    if (storySelect) {
        storySelect.addEventListener("change", (e) => {
            selectedStory = e.target.value;
            applyFilters();
        });
    }

    if (dimSelect) {
        dimSelect.addEventListener("change", (e) => {
            selectedDim = e.target.value;
            applyFilters();
        });
    }

    if (resetBtn) resetBtn.addEventListener("click", resetAllFilters);
    if (clearFiltersBtn) clearFiltersBtn.addEventListener("click", resetAllFilters);

    toggleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            filterMode = button.dataset.filter || "active";
            toggleButtons.forEach((btn) => btn.classList.remove("active"));
            button.classList.add("active");
            applyFilters();
        });
    });

    sortableHeaders.forEach((header) => {
        header.addEventListener("click", () => handleSort(header.dataset.sortKey));
    });

    // Copy functionality
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
        if (!button.dataset.originalTitle) button.dataset.originalTitle = originalTitle;

        const previousTimeout = Number(button.dataset.copyTimeoutId || "0");
        if (previousTimeout) window.clearTimeout(previousTimeout);

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
        if (!copyButton) return;
        const copyText = copyButton.dataset.copyText || copyButton.dataset.surveyId || "";
        const copiedMessage = copyButton.dataset.msgCopied || "Copied";
        if (!copyText) return;
        try {
            await copyWithFallback(copyText);
            showCopyFeedback(copyButton, copiedMessage);
        } catch (error) {
            console.error("Failed to copy:", error);
        }
    });

    populateFilters();
    updateSortHeaderState();
    applyFilters();
});
