
"use strict";

/* =========================
   API configuration
   ========================= */

const API = {
    years: "http://127.0.0.1:8000/sets/years",
    sets: (year) => `http://127.0.0.1:8000/sets/${encodeURIComponent(year)}`,
    rarities: (setId) => `http://127.0.0.1:8000/sets/${encodeURIComponent(setId)}/rarities`,
    variants: (setId) => `http://127.0.0.1:8000/sets/${encodeURIComponent(setId)}/variants`,
    generate: (setId) => `http://127.0.0.1:8000/sets/${encodeURIComponent(setId)}/document`,
};


/* =========================
   HTML elements
   ========================= */

const form = document.querySelector("#set-lister-form");
const yearSelect = document.querySelector("#year-select");
const setSelect = document.querySelector("#set-select");

const rarityOptions = document.querySelector("#rarity-options");
const variantOptions = document.querySelector("#variant-options");

const generateButton = document.querySelector("#generate-button");
const statusMessage = document.querySelector("#status-message");


/* =========================
   API helpers
   ========================= */

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        throw new Error(`Request failed (${response.status}).`);
    }

    return response.json();
}


/* =========================
   Status messages
   ========================= */

function showStatus(message, type = "") {
    statusMessage.textContent = message;
    statusMessage.className = type;
}

function clearStatus() {
    showStatus();
}


/* =========================
   Dropdown helpers
   ========================= */

function resetSelect(select, placeholder) {
    select.replaceChildren();

    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;

    select.appendChild(option);
    select.disabled = true;
}

function addSelectOptions(select, items, placeholder, getValue, getLabel) {
    resetSelect(select, placeholder);

    for (const item of items) {
        const option = document.createElement("option");
        option.value = getValue(item);
        option.textContent = getLabel(item);

        select.appendChild(option);
    }

    select.disabled = items.length === 0;
}


/* =========================
   Checkbox helpers
   ========================= */

function resetFieldset(fieldset, message) {
    fieldset.replaceChildren();

    const legend = document.createElement("legend");
    legend.textContent =
        fieldset === rarityOptions
            ? "Available rarities"
            : "Available variants";

    const emptyMessage = document.createElement("p");
    emptyMessage.className = "empty-message";
    emptyMessage.textContent = message;

    fieldset.append(legend, emptyMessage);
    fieldset.disabled = true;
}

function populateCheckboxes(fieldset, items, name, legendText) {
    const legend = document.createElement("legend");
    legend.textContent = legendText;

    fieldset.replaceChildren(legend);

    for (const item of items) {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.name = name;
        checkbox.value = item;

        checkbox.addEventListener("change", updateGenerateButton);

        label.append(checkbox, document.createTextNode(item));
        fieldset.appendChild(label);
    }

    fieldset.disabled = items.length === 0;
}


/* =========================
   Load release years
   ========================= */

async function loadYears() {
    resetSelect(yearSelect, "Loading years...");
    showStatus("Loading release years...");

    try {
        const years = await fetchJSON(API.years);

        if (!Array.isArray(years)) {
            throw new Error("Expected the years endpoint to return an array.");
        }

        addSelectOptions(
            yearSelect,
            years,
            "Select a year...",
            (year) => String(year),
            (year) => String(year),
        );

        if (years.length === 0) {
            showStatus("No release years were found.");
        } else {
            clearStatus();
        }
    } catch (error) {
        console.error("Failed to load years:", error);
        resetSelect(yearSelect, "Could not load years");
        showStatus("Could not load release years. Please try again.", "error");
    }
}


/* =========================
   Load sets for a year
   ========================= */

async function loadSets(year) {
    resetSelect(setSelect, "Loading sets...");
    resetFieldset(rarityOptions, "Select a set to load its rarities.");
    resetFieldset(variantOptions, "Select a set to load its variants.");
    updateGenerateButton();

    if (!year) {
        resetSelect(setSelect, "Select a year first...");
        clearStatus();
        return;
    }

    showStatus("Loading sets...");

    try {
        const sets = await fetchJSON(API.sets(year));

        if (!Array.isArray(sets)) {
            throw new Error("Expected the sets endpoint to return an array.");
        }

        addSelectOptions(
            setSelect,
            sets,
            "Select a set...",
            (set) => String(set.id),
            (set) => set.name,
        );

        if (sets.length === 0) {
            showStatus("No sets were found for this year.");
        } else {
            clearStatus();
        }
    } catch (error) {
        console.error("Failed to load sets:", error);
        resetSelect(setSelect, "Could not load sets");
        showStatus("Could not load sets. Please try again.", "error");
    }
}


/* =========================
   Load rarities and variants
   ========================= */

async function loadSetOptions(setId) {
    resetFieldset(rarityOptions, "Loading rarities...");
    resetFieldset(variantOptions, "Loading variants...");
    updateGenerateButton();

    if (!setId) {
        resetFieldset(rarityOptions, "Select a set to load its rarities.");
        resetFieldset(variantOptions, "Select a set to load its variants.");
        return;
    }

    showStatus("Loading set options...");

    try {
        const [rarities, variants] = await Promise.all([
            fetchJSON(API.rarities(setId)),
            fetchJSON(API.variants(setId)),
        ]);

        if (!Array.isArray(rarities) || !Array.isArray(variants)) {
            throw new Error("Expected arrays for rarities and variants.");
        }

        populateCheckboxes(
            rarityOptions,
            rarities,
            "rarities",
            "Available rarities",
        );

        populateCheckboxes(
            variantOptions,
            variants,
            "variants",
            "Available variants",
        );

        updateGenerateButton();

        if (rarities.length === 0 || variants.length === 0) {
            showStatus("Some options are unavailable for this set.", "error");
        } else {
            clearStatus();
        }
    } catch (error) {
        console.error("Failed to load set options:", error);

        resetFieldset(rarityOptions, "Could not load rarities.");
        resetFieldset(variantOptions, "Could not load variants.");

        showStatus("Could not load set options. Please try again.", "error");
    }
}


/* =========================
   Form validation
   ========================= */

function getSelectedValues(fieldset) {
    return Array.from(
        fieldset.querySelectorAll('input[type="checkbox"]:checked'),
        (checkbox) => checkbox.value,
    );
}

function updateGenerateButton() {
    const hasYear = yearSelect.value !== "";
    const hasSet = setSelect.value !== "";
    const hasRarities = getSelectedValues(rarityOptions).length > 0;
    const hasVariants = getSelectedValues(variantOptions).length > 0;

    generateButton.disabled = !(
        hasYear &&
        hasSet &&
        hasRarities &&
        hasVariants
    );
}


/* =========================
   Generate document
   ========================= */

async function generateDocument(event) {
    event.preventDefault();

    if (generateButton.disabled) {
        return;
    }

    const setId = setSelect.value;

    const requestData = {
        rarities: getSelectedValues(rarityOptions),
        variants: getSelectedValues(variantOptions),
    };

    generateButton.disabled = true;
    generateButton.textContent = "Generating...";
    showStatus("Generating your document. Please wait...");

    try {
        const result = await fetchJSON(API.generate(setId), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestData),
        });

        if (!result.success) {
            throw new Error("The backend could not generate the document.");
        }

        showStatus(
            "Document generation completed. Your backend currently returns a status response, not a downloadable PDF.",
            "success",
        );
    } catch (error) {
        console.error("Failed to generate document:", error);

        showStatus(
            "Could not generate the document. Please try again.",
            "error",
        );
    } finally {
        generateButton.textContent = "Generate PDF";
        updateGenerateButton();
    }
}


/* =========================
   Event listeners
   ========================= */

yearSelect.addEventListener("change", () => {
    loadSets(yearSelect.value);
});

setSelect.addEventListener("change", () => {
    loadSetOptions(setSelect.value);
});

form.addEventListener("submit", generateDocument);


/* =========================
   Initialize application
   ========================= */

resetSelect(setSelect, "Select a year first...");
resetFieldset(rarityOptions, "Select a set to load its rarities.");
resetFieldset(variantOptions, "Select a set to load its variants.");

loadYears();
