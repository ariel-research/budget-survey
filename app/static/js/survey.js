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
 * Checks if the total is 100 and all inputs are multiples of 5.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateCreateVectorForm() {
    const inputs = document.querySelectorAll('input[type="number"]');
    let total = 0;
    let isValid = true;

    inputs.forEach(input => {
        const value = parseInt(input.value) || 0;
        total += value;
        
        if (value % 5 !== 0) {
            isValid = false;
        }
    });

    if (total !== 100) {
        isValid = false;
    }

    if (!isValid) {
        alert('נא לוודא שהסכום הכולל הוא 100 וכל הערכים מתחלקים ב-5.');
    }

    return isValid;
}

/**
 * Validates the survey form.
 * Checks if all radio button groups have a selected option.
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateSurveyForm() {
    const radioGroups = document.querySelectorAll('input[type="radio"]:checked');
    if (radioGroups.length !== 10) {
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
    const inputs = document.querySelectorAll('input[type="number"]');
    const totalDisplay = document.getElementById('total');
    const submitBtn = document.getElementById('submit-btn');
    const errorDisplay = document.getElementById('error-display');

    if (inputs.length === 3 && totalDisplay && submitBtn && errorDisplay) {
        inputs.forEach(input => {
            input.addEventListener('input', () => updateTotal(inputs, totalDisplay, submitBtn, errorDisplay));
        });
    }
}

/**
 * Updates the total budget allocation and validates inputs in real-time.
 * @param {NodeList} inputs - The list of number input elements.
 * @param {HTMLElement} totalDisplay - The element to display the total.
 * @param {HTMLElement} submitBtn - The submit button element.
 * @param {HTMLElement} errorDisplay - The element to display error messages.
 */
function updateTotal(inputs, totalDisplay, submitBtn, errorDisplay) {
    let total = 0;
    let isValid = true;
    let errorMessage = '';

    inputs.forEach(input => {
        const value = parseInt(input.value) || 0;
        total += value;
        
        if (value % 5 !== 0) {
            isValid = false;
            errorMessage = 'כל המספרים חייבים להתחלק ב-5.';
        }
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
