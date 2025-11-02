/**
 * survey.js - Budget Survey Application
 * Handles client-side interactions for budget creation and survey forms
 * Enhanced with UX improvements for ranking interface
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
        initializeRankingEnhancements(); // NEW: Add UX enhancements
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
            rescale_error_too_small: "Cannot rescale when the total sum is 0",
            ranking_validation_error: "Please rank all options for each question",
            duplicate_ranking_error: "Cannot give the same rank to multiple options"
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

    const inputs = document.querySelectorAll('.budget-input');
    const values = Array.from(inputs).map(input => parseInt(input.value) || 0);
    const hasNonDivisibleBy5 = values.some(val => val % 5 !== 0);

    let errorMessage = '';
    if (nonZeroDepartments < CONFIG.MIN_DEPARTMENTS) {
        errorMessage = state.messages.min_two_departments;
    } else if (hasNonDivisibleBy5) {
        errorMessage = state.messages.invalid_vector;
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
    const hasNonDivisibleBy5 = values.some(val => val % 5 !== 0);
    const isValid = total === CONFIG.TOTAL_EXPECTED && 
                   nonZeroDepartments >= CONFIG.MIN_DEPARTMENTS &&
                   !hasNonDivisibleBy5;

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

    // Update rescale button - enabled when form is invalid OR unusable
    // Disabled only when form is already valid OR unusable (total=0 or too many zeros)
    elements.rescale.disabled = 
        total === 0 ||                                    // Can't rescale from zero
        (isValid) ||                                      // Form is already valid
        values.some(val => isNaN(val)) ||                // Has invalid numbers
        zeroCount > 1;                                    // Too many zeros
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

    // Check if this is a ranking-based survey
    const rankingQuestions = document.querySelectorAll('.ranking-question');
    if (rankingQuestions.length > 0) {
        initializeRankingValidation(form, submitBtn);
        return;
    }

    // Traditional radio-based survey
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
 * Initialize ranking validation for ranking-based surveys
 */
function initializeRankingValidation(form, submitBtn) {
    const rankingQuestions = document.querySelectorAll('.ranking-question');
    console.log(`Detected ${rankingQuestions.length} ranking questions`);

    // Set up event listeners for all option ranking dropdowns
    rankingQuestions.forEach((question, questionIndex) => {
        const dropdowns = question.querySelectorAll('.option-rank-dropdown');
        const optionCards = question.querySelectorAll('.option-card');
        
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('change', function() {
                updateHiddenRankFields(question);
                validateSingleQuestion(question);
                updateVisualFeedback(question);
                updateRankingSubmitButtonState(submitBtn);
                updateSelectionFeedback(question);
            });

            // Focus/blur events for highlighting
            dropdown.addEventListener('focus', function() {
                const optionLetter = this.getAttribute('data-option');
                highlightOption(question, optionLetter);
            });
            
            dropdown.addEventListener('blur', function() {
                clearHighlights(question);
            });

            // Keyboard navigation
            dropdown.addEventListener('keydown', function(e) {
                const currentIndex = Array.from(dropdowns).indexOf(this);
                
                // Arrow key navigation between dropdowns
                if (e.key === 'ArrowDown' && currentIndex < dropdowns.length - 1) {
                    e.preventDefault();
                    dropdowns[currentIndex + 1].focus();
                } else if (e.key === 'ArrowUp' && currentIndex > 0) {
                    e.preventDefault();
                    dropdowns[currentIndex - 1].focus();
                }
            });
        });
    });

    // Set up form submission validation
    form.addEventListener('submit', handleRankingSubmission);
    
    // Initial button state update
    updateRankingSubmitButtonState(submitBtn);
}

/**
 * Update hidden rank fields based on integrated dropdown selections
 * Maps from option-based rankings (A=1, B=2, C=3) to rank-based format (rank_1=A, rank_2=B, rank_3=C)
 */
function updateHiddenRankFields(question) {
    const questionNumber = question.getAttribute('data-question');
    const dropdowns = question.querySelectorAll('.option-rank-dropdown');
    const hiddenFields = question.querySelectorAll('.hidden-rank-field');
    
    // Clear all hidden fields first
    hiddenFields.forEach(field => field.value = '');
    
    // Map from option rankings to rank assignments
    dropdowns.forEach(dropdown => {
        const option = dropdown.getAttribute('data-option');
        const rank = dropdown.value;
        
        if (rank) {
            // Find the corresponding hidden field for this rank
            const hiddenField = question.querySelector(`.hidden-rank-field[data-rank="${rank}"]`);
            if (hiddenField) {
                hiddenField.value = option;
            }
        }
    });
}

/**
 * Visual connection between options and rankings
 */
function initializeRankingEnhancements() {
    const rankingQuestions = document.querySelectorAll('.ranking-question');
    
    rankingQuestions.forEach(question => {
        const optionCards = question.querySelectorAll('.option-card');
        
        // Add option letter attributes for CSS styling
        optionCards.forEach((card, index) => {
            const letter = ['A', 'B', 'C'][index];
            const header = card.querySelector('.option-header h4');
            if (header) {
                header.setAttribute('data-option-letter', letter);
            }
            
            // Add data attributes for the card itself
            card.setAttribute('data-option-letter', letter);
        });
    });
}

/**
 * Highlight option when focused in dropdown
 */
function highlightOption(question, optionLetter) {
    // Clear existing highlights
    clearHighlights(question);
    
    if (optionLetter) {
        const optionIndex = ['A', 'B', 'C'].indexOf(optionLetter);
        const optionCard = question.querySelectorAll('.option-card')[optionIndex];
        if (optionCard) {
            optionCard.classList.add('highlight');
        }
    }
}

/**
 * Clear all option highlights
 */
function clearHighlights(question) {
    question.querySelectorAll('.option-card').forEach(card => {
        card.classList.remove('highlight');
    });
}

/**
 * Update selection feedback with progress indicators
 */
function updateSelectionFeedback(question) {
    const dropdowns = question.querySelectorAll('.option-rank-dropdown');
    const optionCards = question.querySelectorAll('.option-card');
    
    // Update individual option card states
    dropdowns.forEach(dropdown => {
        const option = dropdown.getAttribute('data-option');
        const card = question.querySelector(`[data-option="${option}"]`);
        
        if (card) {
            if (dropdown.value) {
                card.classList.add('option-ranked');
            } else {
                card.classList.remove('option-ranked');
            }
        }
    });
}

/**
 * Validate ranking for a single question
 */
function validateSingleQuestion(question) {
    const dropdowns = question.querySelectorAll('.option-rank-dropdown');
    const values = Array.from(dropdowns).map(d => d.value).filter(v => v);
    const hasDuplicates = values.length !== new Set(values).size;
    const isComplete = values.length === 3;
    
    const feedback = question.querySelector('.ranking-feedback');
    
    // Clear previous states
    dropdowns.forEach(dropdown => {
        dropdown.classList.remove('error', 'completed');
        dropdown.parentElement.parentElement.classList.remove('ranking-error');
    });
    
    if (hasDuplicates) {
        // Show duplicate error
        feedback.textContent = state.messages.duplicate_ranking_error || 
                              'Cannot give the same rank to multiple options';
        feedback.className = 'ranking-feedback error';
        feedback.style.display = 'block';
        
        // Mark conflicting dropdowns
        const valueCounts = {};
        dropdowns.forEach(dropdown => {
            if (dropdown.value) {
                valueCounts[dropdown.value] = (valueCounts[dropdown.value] || 0) + 1;
                if (valueCounts[dropdown.value] > 1) {
                    dropdown.classList.add('error');
                    dropdown.parentElement.parentElement.classList.add('ranking-error');
                }
            }
        });
        
        return false;
    } else if (!isComplete) {
        // Show incomplete message if any dropdown has been touched
        const touchedDropdowns = Array.from(dropdowns).filter(d => d.value);
        if (touchedDropdowns.length > 0) {
            feedback.textContent = state.messages.ranking_validation_error || 
                                  'Please rank all options for each question';
            feedback.className = 'ranking-feedback error';
            feedback.style.display = 'block';
        } else {
            feedback.style.display = 'none';
        }
        return false;
    } else {
        // All good - hide feedback and mark as completed
        feedback.style.display = 'none';
        dropdowns.forEach(dropdown => {
            if (dropdown.value) {
                dropdown.classList.add('completed');
                dropdown.parentElement.parentElement.classList.add('ranking-completed');
            }
        });
        return true;
    }
}

/**
 * Update visual feedback for option cards based on selections
 */
function updateVisualFeedback(question) {
    const dropdowns = question.querySelectorAll('.option-rank-dropdown');
    const optionCards = question.querySelectorAll('.option-card');
    
    // Clear all ranking states
    optionCards.forEach(card => {
        card.classList.remove('ranked-1', 'ranked-2', 'ranked-3');
        card.removeAttribute('data-rank');
    });
    
    // Apply ranking states based on selections
    dropdowns.forEach(dropdown => {
        const option = dropdown.getAttribute('data-option');
        const rank = dropdown.value;
        const card = question.querySelector(`[data-option="${option}"]`);
        
        if (card && rank) {
            card.classList.add(`ranked-${rank}`);
            card.setAttribute('data-rank', rank);
        }
    });
}

/**
 * Update submit button state for ranking surveys
 */
function updateRankingSubmitButtonState(submitBtn) {
    const rankingQuestions = document.querySelectorAll('.ranking-question');
    let allValid = true;
    let totalQuestions = rankingQuestions.length;
    let validQuestions = 0;
    
    rankingQuestions.forEach(question => {
        const isValid = validateSingleQuestion(question);
        if (isValid) {
            validQuestions++;
            // Mark question as complete
            question.classList.add('question-complete');
        } else {
            allValid = false;
            question.classList.remove('question-complete');
        }
    });
    
    // Update submit button
    submitBtn.disabled = !allValid;
    submitBtn.classList.toggle('btn-disabled', !allValid);
    
    // Progress feedback
    const progressText = allValid ? 
        'Ready to submit' : 
        `Complete all rankings (${validQuestions}/${totalQuestions})`;
    submitBtn.title = progressText;
    
    // Add pulse animation when all complete
    if (allValid && !state.wasSubmitEnabled) {
        state.wasSubmitEnabled = true;
        submitBtn.classList.add('btn-pulse');
        setTimeout(() => submitBtn.classList.remove('btn-pulse'), 1000);
    }
    if (!allValid) state.wasSubmitEnabled = false;
}

/**
 * Handle ranking survey form submission
 */
function handleRankingSubmission(e) {
    e.preventDefault();
    
    const rankingQuestions = document.querySelectorAll('.ranking-question');
    let hasErrors = false;
    let awarenessError = false;
    
    // Validate all questions one final time
    rankingQuestions.forEach(question => {
        if (!validateSingleQuestion(question)) {
            hasErrors = true;
            
            // Check if this is an awareness question that failed
            if (question.classList.contains('awareness-question')) {
                awarenessError = true;
            }
        }
    });
    
    if (hasErrors) {
        // Show specific message for awareness check failure
        if (awarenessError) {
            showAlert(state.messages.failed_awareness || 
                     'Failed awareness check. Please try again and pay attention to the questions.');
        } else {
            showAlert(state.messages.ranking_validation_error || 
                     'Please complete all rankings before submitting');
        }
        
        // Scroll to first error
        const firstError = document.querySelector('.ranking-feedback.error');
        if (firstError) {
            firstError.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }
        return;
    }
    
    // All validations passed - submit the form
    e.target.submit();
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