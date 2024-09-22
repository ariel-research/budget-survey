/**
 * survey.js
 * This script handles client-side interactions for the budget survey application.
 * It manages form submission validation, real-time budget allocation calculations,
 * and error displays for the create vector and survey pages.
 */

document.addEventListener('DOMContentLoaded', function() {
    setupFormSubmission();
    setupBudgetVectorCreation();
});

/**
 * Sets up the form submission event listener.
 * This function is used on both the create vector and survey pages.
 */
function setupFormSubmission() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    }
}

/**
 * Handles the form submission event.
 * Validates the form based on its type (create vector or survey).
 * @param {Event} e - The submit event object.
 */
function handleFormSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const formType = form.getAttribute('data-form-type');
    
    let isValid = false;
    
    if (formType === 'create-vector') {
        isValid = validateCreateVectorForm();
    } else if (formType === 'survey') {
        isValid = validateSurveyForm();
    }

    if (isValid) {
        form.submit();
    }
}

/**
 * Validates the create vector form.
 * Checks if the total is 100.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateCreateVectorForm() {
    const selects = document.querySelectorAll('select');
    let total = 0;

    selects.forEach(select => {
        total += parseInt(select.value) || 0;
    });

    if (total !== 100) {
        alert('נא לוודא שהסכום הכולל הוא 100.');
        return false;
    }

    return true;
}

/**
 * Validates the survey form.
 * Checks if all radio button groups have a selected option.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateSurveyForm() {
    const radioGroups = document.querySelectorAll('input[type="radio"]:checked');
    if (radioGroups.length !== 11) { // 10 comparison pairs + 1 awareness check
        alert('נא לבחור אפשרות אחת עבור כל זוג.');
        return false;
    }
    return true;
}

/**
 * Sets up the budget vector creation functionality.
 * This includes real-time total calculation and input validation.
 */
function setupBudgetVectorCreation() {
    const selects = document.querySelectorAll('select');
    const totalDisplay = document.getElementById('total');
    const submitBtn = document.getElementById('submit-btn');
    const errorDisplay = document.getElementById('error-display');

    if (selects.length > 0 && totalDisplay && submitBtn && errorDisplay) {
        selects.forEach(select => {
            select.addEventListener('change', () => updateTotal(selects, totalDisplay, submitBtn, errorDisplay));
        });
    }
}

/**
 * Updates the total budget allocation and validates selects in real-time.
 * @param {NodeList} selects - The list of number select elements.
 * @param {HTMLElement} totalDisplay - The element to display the total.
 * @param {HTMLElement} submitBtn - The submit button element.
 * @param {HTMLElement} errorDisplay - The element to display error messages.
 */
function updateTotal(selects, totalDisplay, submitBtn, errorDisplay) {
    let total = 0;
    let isValid = true;
    let errorMessage = '';

    selects.forEach(select => {
        const value = parseInt(select.value) || 0;
        total += value;
    });

    totalDisplay.textContent = total;
    
    if (total !== 100) {
        isValid = false;
        errorMessage = 'הסכום הכולל חייב להיות בדיוק 100.';
    }

    submitBtn.disabled = !isValid;
    totalDisplay.style.color = isValid ? '#27ae60' : '#e74c3c';

    if (!isValid) {
        errorDisplay.textContent = errorMessage;
        errorDisplay.style.display = 'block';
    } else {
        errorDisplay.style.display = 'none';
    }
}
