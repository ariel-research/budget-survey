/**
 * survey.js - Budget Survey Application
 * Handles client-side interactions for budget creation and survey forms
 */

// Configuration object for constants and settings
const CONFIG = {
    TOTAL_EXPECTED: 100,
    TOTAL_QUESTIONS: 12, // 10 comparison pairs + 2 awareness check
    MIN_DEPARTMENTS: 2,
    MIN_ALLOCATION: 5,
    SCALING_STEP: 5,
    COLORS: {
        PERFECT: '#27ae60',
        OVER: '#e67e22',
        UNDER: '#e74c3c'
    }
};

// State management for the application
const state = {
    messages: {},
    wasSubmitEnabled: false
};

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadMessages();
        initializeForm();
        initializeAlerts();
    } catch (error) {
        console.error('Initialization failed:', error);
    }
});

/**
 * Load error messages from the server
 */
async function loadMessages() {
    try {
        const response = await fetch('/get_messages');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        state.messages = await response.json();
    } catch (error) {
        console.error('Failed to load messages:', error);
        // Fallback messages
        state.messages = {
            total_not_100: "Please ensure the total sum is 100.",
            choose_all_pairs: "Please choose one option for each pair.",
            invalid_vector: "The sum must be 100 and each number must be divisible by 5.",
            min_two_departments: "Budget must be allocated to at least two departments.",
            rescale_error_too_small: "Cannot rescale when the total sum is 0"
        };
    }
}

/**
 * Initialize the appropriate form based on data-form-type
 */
function initializeForm() {
    const formType = document.querySelector('form')?.getAttribute('data-form-type');
    formType === 'create-vector' ? initializeBudgetForm() : initializeSurveyForm();
}

/**
 * Initialize budget creation form
 */
function initializeBudgetForm() {
    const elements = {
        inputs: document.querySelectorAll('.budget-input'),
        total: document.getElementById('total'),
        submit: document.getElementById('submit-btn'),
        rescale: document.getElementById('rescale-btn'),
        error: document.getElementById('error-display')
    };

    if (!validateElements(elements)) return;

    // Set up event listeners
    elements.inputs.forEach(input => {
        input.addEventListener('input', handleInputChange);
        input.addEventListener('change', handleInputChange);
    });

    elements.rescale.addEventListener('click', () => handleRescale(elements));

    // Initialize form state
    updateFormState(elements);

    function handleInputChange() {
        let value = parseInt(this.value) || 0;
        this.value = Math.max(0, value) || '0';
        updateFormState(elements);
    }
}

/**
 * Validate that all required elements are present
 */
function validateElements(elements) {
    const missing = Object.entries(elements)
        .filter(([key, value]) => !value || (value instanceof NodeList && !value.length))
        .map(([key]) => key);

    if (missing.length) {
        console.warn(`Missing required elements: ${missing.join(', ')}`);
        return false;
    }
    return true;
}

/**
 * Update the form state and UI
 */
function updateFormState(elements) {
    const values = Array.from(elements.inputs).map(input => parseInt(input.value) || 0);
    const total = values.reduce((sum, val) => sum + val, 0);
    const nonZeroDepartments = values.filter(val => val > 0).length;

    updateTotalDisplay(elements.total, total);
    updateErrorDisplay(elements.error, total, nonZeroDepartments);
    updateButtonStates(elements, {
        total,
        values,
        nonZeroDepartments,
        zeroCount: values.filter(val => val === 0).length
    });
}

/**
 * Update total display with appropriate styling
 */
function updateTotalDisplay(totalElement, total) {
    if (!totalElement) return;
    
    totalElement.textContent = total;
    const status = total === CONFIG.TOTAL_EXPECTED ? 'perfect' : 
                  total > CONFIG.TOTAL_EXPECTED ? 'over' : 'under';
    
    totalElement.dataset.status = status;
    totalElement.style.color = CONFIG.COLORS[status.toUpperCase()];
}

/**
 * Update error display based on validation
 */
function updateErrorDisplay(errorElement, total, nonZeroDepartments) {
    if (!errorElement) return;

    let errorMessage = '';
    if (nonZeroDepartments < CONFIG.MIN_DEPARTMENTS) {
        errorMessage = state.messages.min_two_departments;
    } else if (total !== CONFIG.TOTAL_EXPECTED) {
        errorMessage = state.messages.total_not_100;
    }

    errorElement.textContent = errorMessage;
    errorElement.style.display = errorMessage ? 'block' : 'none';
}

/**
 * Update submit and rescale button states
 */
function updateButtonStates(elements, { total, values, nonZeroDepartments, zeroCount }) {
    const isValid = total === CONFIG.TOTAL_EXPECTED && nonZeroDepartments >= CONFIG.MIN_DEPARTMENTS;

    // Update submit button
    elements.submit.disabled = !isValid;
    elements.submit.classList.toggle('btn-disabled', !isValid);

    // Add pulse animation when enabled
    if (isValid && !state.wasSubmitEnabled) {
        state.wasSubmitEnabled = true;
        elements.submit.classList.add('btn-pulse');
        setTimeout(() => elements.submit.classList.remove('btn-pulse'), 1000);
    }
    if (!isValid) state.wasSubmitEnabled = false;

    // Update rescale button
    elements.rescale.disabled = total === 0 || 
                              total === CONFIG.TOTAL_EXPECTED || 
                              values.some(val => isNaN(val)) ||
                              zeroCount > 1;
}

/**
 * Handle rescaling of budget values
 */
function handleRescale(elements) {
    const values = Array.from(elements.inputs).map(input => parseInt(input.value) || 0);
    const total = values.reduce((sum, val) => sum + val, 0);

    if (total === 0) {
        showAlert(state.messages.rescale_error_too_small);
        return;
    }

    const scaledValues = calculateScaledValues(values, total);
    
    // Update input values
    elements.inputs.forEach((input, index) => {
        input.value = scaledValues[index];
    });

    updateFormState(elements);
}

/**
 * Calculate scaled values ensuring minimum allocations and correct total
 */
function calculateScaledValues(values, total) {
    // First pass: Calculate scaled values
    let scaled = values.map(value => {
        if (value === 0) return 0;
        let scaled = (value * CONFIG.TOTAL_EXPECTED / total);
        return Math.max(CONFIG.MIN_ALLOCATION, 
                       Math.round(scaled / CONFIG.SCALING_STEP) * CONFIG.SCALING_STEP);
    });

    // Second pass: Adjust to ensure total is exactly 100
    let newTotal = scaled.reduce((sum, val) => sum + val, 0);
    if (newTotal !== CONFIG.TOTAL_EXPECTED) {
        const maxIndex = scaled.indexOf(Math.max(...scaled));
        const adjustment = CONFIG.TOTAL_EXPECTED - newTotal;
        scaled[maxIndex] += adjustment;
    }

    return scaled;
}

/**
 * Initialize survey form
 */
function initializeSurveyForm() {
    const form = document.querySelector('form');
    const submitBtn = document.querySelector('.btn[type="submit"]');

    if (!form || !submitBtn) {
        console.warn('Survey form or submit button not found');
        return;
    }

    // Dynamically count the total number of radio groups on the page
    const radioGroups = new Set();
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        radioGroups.add(radio.name);
        radio.addEventListener('change', () => updateSubmitButtonState(submitBtn));
    });
    
    // Update the CONFIG to match the actual number of question pairs
    CONFIG.TOTAL_QUESTIONS = radioGroups.size;
    console.log(`Detected ${CONFIG.TOTAL_QUESTIONS} question pairs in this survey`);

    form.addEventListener('submit', handleSurveySubmission);
    updateSubmitButtonState(submitBtn);
}

/**
 * Update survey form submit button state
 */
function updateSubmitButtonState(submitBtn) {
    const selectedPairs = document.querySelectorAll('input[type="radio"]:checked').length;
    const isComplete = selectedPairs === CONFIG.TOTAL_QUESTIONS;

    submitBtn.disabled = !isComplete;
    submitBtn.classList.toggle('btn-disabled', !isComplete);
    submitBtn.title = isComplete ? '' : state.messages.choose_all_pairs;
}

/**
 * Handle survey form submission, validating all radio groups are answered
 */
function handleSurveySubmission(e) {
    e.preventDefault();
    
    const radioGroups = document.querySelectorAll('input[type="radio"]:checked');
    if (radioGroups.length !== CONFIG.TOTAL_QUESTIONS) {
        showAlert(state.messages.choose_all_pairs);
        return;
    }
    
    e.target.submit();
}

/**
 * Initialize custom alert system
 */
function initializeAlerts() {
    const alertHTML = `
        <div id="customAlert" class="custom-alert">
            <div class="alert-content">
                <p id="alertMessage"></p>
                <button id="alertClose">OK</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', alertHTML);

    const alert = document.getElementById('customAlert');
    const closeBtn = document.getElementById('alertClose');

    closeBtn.onclick = () => alert.style.display = "none";
    window.onclick = (event) => {
        if (event.target === alert) {
            alert.style.display = "none";
        }
    };
}

/**
 * Show custom alert with message
 */
function showAlert(message) {
    const alert = document.getElementById('customAlert');
    const alertMessage = document.getElementById('alertMessage');
    
    if (!alert || !alertMessage) {
        console.error('Custom alert elements not found');
        return;
    }
    
    alertMessage.textContent = message;
    alert.style.display = "block";
}
