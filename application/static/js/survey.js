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
        const formType = document.querySelector('form')?.getAttribute('data-form-type');
        
        if (formType === 'create-vector') {
            initializeBudgetForm();
        } else {
            initializeSurveyForm();
        }
        
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
            total_not_100: "Please ensure the total sum is 100.",
            choose_all_pairs: "Please choose one option for each pair.",
            invalid_vector: "The sum must be 100 and each number must be divisible by 5."
        };
    }
}

/**
 * Initializes the budget creation form with number inputs and rescale functionality.
 */
function initializeBudgetForm() {
    const inputs = document.querySelectorAll('.budget-input');
    const totalElement = document.getElementById('total');
    const submitBtn = document.getElementById('submit-btn');
    const rescaleBtn = document.getElementById('rescale-btn');
    const errorDisplay = document.getElementById('error-display');

    if (!inputs.length || !totalElement || !submitBtn || !rescaleBtn || !errorDisplay) {
        console.warn('Required elements for budget form not found');
        return;
    }

    // Input validation and formatting
    inputs.forEach(input => {
        // Handle input while typing
        input.addEventListener('input', function() {
            // Allow any non-negative integer
            let value = parseInt(this.value) || 0;
            value = Math.max(0, value); // Only ensure it's not negative
            this.value = value || '0'; // Always show 0 instead of empty
            updateFormState();
        });

        // Handle change event (triggered by up/down buttons)
        input.addEventListener('change', function() {
            if (!this.value || this.value === '') {
                this.value = '0';
            }
            updateFormState();
        });
    });

    // Rescale button handler
    rescaleBtn.addEventListener('click', handleRescale);

    /**
     * Updates the total display with appropriate styling based on the current total.
     * @param {number} total - The current total value
     */
    function updateTotalDisplay(total) {
        if (!totalElement) return;
        
        totalElement.textContent = total;
        
        // Update the status and color based on total value
        if (total === TOTAL_EXPECTED) {
            totalElement.dataset.status = 'perfect';
            totalElement.style.color = '#27ae60'; // green
        } else if (total > TOTAL_EXPECTED) {
            totalElement.dataset.status = 'over';
            totalElement.style.color = '#e67e22'; // orange
        } else {
            totalElement.dataset.status = 'under';
            totalElement.style.color = '#e74c3c'; // red
        }
    }

    /**
     * Updates the submit button state and styling based on form validity.
     * The button will be enabled only when:
     * 1. The total sum is exactly 100
     * 2. At least two values are positive
     * @param {Array<number>} values - Array of current input values
     */
    function updateSubmitButton(values) {
        if (!submitBtn) return;

        const total = values.reduce((sum, val) => sum + val, 0);
        const positiveValuesCount = values.filter(val => val > 0).length;
        
        const isValid = total === TOTAL_EXPECTED && positiveValuesCount >= 2;
        
        // Update button state and styling
        submitBtn.disabled = !isValid;
        submitBtn.classList.toggle('btn-disabled', !isValid);
        
        // Add pulse animation when becoming valid
        if (isValid && !submitBtn.dataset.wasEnabled) {
            submitBtn.dataset.wasEnabled = 'true';
            submitBtn.classList.add('btn-pulse');
            setTimeout(() => submitBtn.classList.remove('btn-pulse'), 1000);
        }
        
        // Reset the wasEnabled flag when becoming invalid
        if (!isValid) {
            submitBtn.dataset.wasEnabled = 'false';
        }
    }

    /**
     * Updates the form state including total, button states, and error messages.
     */
    function updateFormState() {
        const values = Array.from(inputs).map(input => parseInt(input.value) || 0);
        const total = values.reduce((sum, val) => sum + val, 0);
        
        // Update total display
        updateTotalDisplay(total);
        
        // Update submit button state with values array
        updateSubmitButton(values);
        
        // Update rescale button state
        rescaleBtn.disabled = total === 0 || total === TOTAL_EXPECTED || 
                            values.some(val => isNaN(val));
        
        // Update error display for total sum
        errorDisplay.textContent = total !== TOTAL_EXPECTED ? messages.total_not_100 : '';
        errorDisplay.style.display = total !== TOTAL_EXPECTED ? 'block' : 'none';
    }

    /**
     * Handles the rescale button click event.
     */
    function handleRescale() {
        const values = Array.from(inputs).map(input => parseInt(input.value) || 0);
        const total = values.reduce((sum, val) => sum + val, 0);
        
        if (total === 0) {
            showAlert(messages.rescale_error_too_small);
            return;
        }
    
        // Check for multiple zeros
        const zeroCount = values.filter(val => val === 0).length;
        if (zeroCount > 1) {
            showAlert(messages.rescale_error_too_many_zeros);
            return;
        }
    
        // First pass: Calculate scaled values
        let scaledValues = values.map(value => {
            if (value === 0) return 0; // Keep zeros as zeros
            // For non-zero values, ensure minimum of 5 after scaling
            let scaled = (value * TOTAL_EXPECTED / total);
            return Math.max(5, Math.round(scaled / 5) * 5);
        });
    
        // Second pass: Adjust to ensure total is exactly 100
        let newTotal = scaledValues.reduce((sum, val) => sum + val, 0);
        if (newTotal !== TOTAL_EXPECTED) {
            // Find the largest value and adjust it
            const maxIndex = scaledValues.indexOf(Math.max(...scaledValues));
            // Ensure we don't go below 5 for non-zero values
            const adjustment = TOTAL_EXPECTED - newTotal;
            const newValue = scaledValues[maxIndex] + adjustment;
            if (newValue >= 5) {
                scaledValues[maxIndex] = newValue;
            } else {
                // If adjustment would make the value too small, 
                // redistribute among other non-zero values
                const nonZeroIndices = scaledValues
                    .map((val, idx) => val > 0 ? idx : -1)
                    .filter(idx => idx !== -1 && idx !== maxIndex);
                
                if (nonZeroIndices.length > 0) {
                    const redistributeAmount = Math.abs(newValue - 5);
                    scaledValues[maxIndex] = 5;
                    const largestOtherIndex = nonZeroIndices.reduce((maxIdx, idx) => 
                        scaledValues[idx] > scaledValues[maxIdx] ? idx : maxIdx, 
                        nonZeroIndices[0]);
                    scaledValues[largestOtherIndex] -= redistributeAmount;
                }
            }
        }
    
        // Update input values
        inputs.forEach((input, index) => {
            input.value = scaledValues[index];
        });
    
        updateFormState();
    }

    // Initial state update
    updateFormState();
}

/**
 * Initializes the survey form for comparison pairs.
 */
function initializeSurveyForm() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleSurveySubmission);
    } else {
        console.warn('Survey form element not found');
    }
}

/**
 * Handles survey form submission, validating all radio groups are answered.
 * @param {Event} e - The submit event object
 */
function handleSurveySubmission(e) {
    e.preventDefault();
    
    const radioGroups = document.querySelectorAll('input[type="radio"]:checked');
    if (radioGroups.length !== TOTAL_RADIO_GROUPS) {
        showAlert(messages.choose_all_pairs);
        return;
    }
    
    e.target.submit();
}

/**
 * Creates and appends the custom alert element to the document body.
 */
function createAlertElement() {
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
        if (event.target == alert) {
            alert.style.display = "none";
        }
    };
}

/**
 * Displays a custom alert with the given message.
 * @param {string} message - The message to display in the alert
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
