/**
 * survey.js
 * This script handles client-side interactions for the budget survey application.
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    }

    setupBudgetVectorCreation();
    createAlertElement();
});

/**
 * Handles form submission, preventing default action and validating based on form type.
 * @param {Event} e - The submit event object.
 */
function handleFormSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const formType = form.getAttribute('data-form-type');
    
    let isValid = formType === 'create-vector' ? validateCreateVectorForm() : validateSurveyForm();

    if (isValid) {
        form.submit();
    }
}

/**
 * Validates the create vector form, ensuring the total is exactly 100.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateCreateVectorForm() {
    const selects = document.querySelectorAll('select');
    let total = Array.from(selects).reduce((sum, select) => sum + (parseInt(select.value) || 0), 0);

    if (total !== 100) {
        showAlert('נא לוודא שהסכום הכולל הוא 100.');
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
    if (radioGroups.length !== 11) { // 10 comparison pairs + 1 awareness check
        showAlert('נא לבחור אפשרות אחת עבור כל זוג.');
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
            let total = Array.from(selects).reduce((sum, select) => sum + (parseInt(select.value) || 0), 0);
            totalDisplay.textContent = total;
            
            let isValid = total === 100;
            submitBtn.disabled = !isValid;
            totalDisplay.style.color = isValid ? '#27ae60' : '#e74c3c';
            errorDisplay.textContent = isValid ? '' : 'נא לוודא שהסכום הכולל הוא 100.';
            errorDisplay.style.display = isValid ? 'none' : 'block';
        };

        selects.forEach(select => select.addEventListener('change', updateTotal));
        updateTotal(); // Initial update
    }
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
    alertMessage.textContent = message;
    alert.style.display = "block";
}