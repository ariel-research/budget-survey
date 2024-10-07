/**
 * survey.js
 * This script handles client-side interactions for the budget survey application.
 */

// Constants
const TOTAL_EXPECTED = 100;
const TOTAL_RADIO_GROUPS = 11; // 10 comparison pairs + 1 awareness check

// The error messages
let messages = {};

/**
 * Initializes the survey application when the DOM is fully loaded.
 */
document.addEventListener('DOMContentLoaded', async function() {
    try {
        await loadMessages();
        initializeForm();
        setupBudgetVectorCreation();
        createAlertElement();
    } catch (error) {
        console.error('Initialization failed:', error);
    }
});

/**
 * Loads error messages from the server.
 */
async function loadMessages() {
    try {
        const response = await fetch('/get_messages');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        messages = await response.json();
    } catch (error) {
        console.error('Failed to load messages:', error);
        messages = {
            total_not_100: "נא לוודא שהסכום הכולל הוא 100.",
            choose_all_pairs: "נא לבחור אפשרות אחת עבור כל זוג.",
        };
    }
}

/**
 * Initializes the form event listener.
 */
function initializeForm() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    } else {
        console.warn('Form element not found');
    }
}

/**
 * Handles form submission, preventing default action and validating based on form type.
 * @param {Event} e - The submit event object.
 */
function handleFormSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const formType = form.getAttribute('data-form-type');
    
    const isValid = formType === 'create-vector' ? validateCreateVectorForm() : validateSurveyForm();

    if (isValid) {
        form.submit();
    }
}

/**
 * Validates the create vector form, ensuring the total is exactly TOTAL_EXPECTED.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateCreateVectorForm() {
    const selects = document.querySelectorAll('select');
    const total = calculateTotal(selects);

    if (total !== TOTAL_EXPECTED) {
        showAlert(messages.total_not_100);
        return false;
    }
    return true;
}

/**
 * Validates the survey form, ensuring all radio button groups are answered.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateSurveyForm() {
    const radioGroups = document.querySelectorAll('input[type="radio"]:checked');
    if (radioGroups.length !== TOTAL_RADIO_GROUPS) {
        showAlert(messages.choose_all_pairs);
        return false;
    }
    return true;
}

/**
 * Sets up real-time budget vector creation and validation.
 */
function setupBudgetVectorCreation() {
    const selects = document.querySelectorAll('select');
    const totalDisplay = document.getElementById('total');
    const submitBtn = document.getElementById('submit-btn');
    const errorDisplay = document.getElementById('error-display');

    if (selects.length > 0 && totalDisplay && submitBtn && errorDisplay) {
        const updateTotal = () => {
            const total = calculateTotal(selects);
            updateUI(total, totalDisplay, submitBtn, errorDisplay);
        };

        selects.forEach(select => select.addEventListener('change', updateTotal));
        updateTotal(); // Initial update
    } else {
        console.warn('Required elements for budget vector creation not found');
    }
}

/**
 * Calculates the total from select elements.
 * @param {NodeList} selects - The select elements.
 * @returns {number} The calculated total.
 */
function calculateTotal(selects) {
    return Array.from(selects).reduce((sum, select) => sum + (parseInt(select.value) || 0), 0);
}

/**
 * Updates the UI based on the current total.
 * @param {number} total - The current total.
 * @param {HTMLElement} totalDisplay - The element to display the total.
 * @param {HTMLElement} submitBtn - The submit button element.
 * @param {HTMLElement} errorDisplay - The element to display error messages.
 */
function updateUI(total, totalDisplay, submitBtn, errorDisplay) {
    const isValid = total === TOTAL_EXPECTED;
    totalDisplay.textContent = total;
    submitBtn.disabled = !isValid;
    totalDisplay.style.color = isValid ? '#27ae60' : '#e74c3c';
    errorDisplay.textContent = isValid ? '' : (messages.total_not_100 || 'נא לוודא שהסכום הכולל הוא 100.');
    errorDisplay.style.display = isValid ? 'none' : 'block';
}

/**
 * Creates and appends the custom alert element to the document body.
 */
function createAlertElement() {
    const alertHTML = `
        <div id="customAlert" class="custom-alert">
            <div class="alert-content">
                <p id="alertMessage"></p>
                <button id="alertClose">אישור</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', alertHTML);

    const alert = document.getElementById('customAlert');
    const closeBtn = document.getElementById('alertClose');

    closeBtn.onclick = () => alert.style.display = "none";
    window.onclick = (event) => {
        if (event.target == alert) {
            alert.style.display = "none";
        }
    };
}

/**
 * Displays a custom alert with the given message.
 * @param {string} message - The message to display in the alert.
 */
function showAlert(message) {
    const alert = document.getElementById('customAlert');
    const alertMessage = document.getElementById('alertMessage');
    if (alert && alertMessage) {
        alertMessage.textContent = message;
        alert.style.display = "block";
    } else {
        console.error('Custom alert elements not found');
    }
}