/**
 * blacklisted.js - Handles functionality for the blacklisted user page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get the close button
    const closeButton = document.querySelector('.close-btn');
    
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            // Try multiple closing strategies in order of preference
            closeWindow();
        });
    }
});

/**
 * Attempts to close the current window using multiple strategies
 * for maximum browser compatibility
 */
function closeWindow() {
    // Strategy 1: Try direct window.close() first
    try {
        window.close();
    } catch (e) {
        console.log("Standard window.close() failed, trying alternative methods");
    }
    
    // Strategy 2: Check if we have an opener and we're in a popup
    if (window.opener && !window.opener.closed) {
        window.close();
    }
    
    // Strategy 3: Alternative method that sometimes works in Firefox/IE
    try {
        const win = window.open('', '_self');
        win.close();
    } catch (e) {
        console.log("Alternative window.close() method failed");
    }
    
    // Strategy 4: As a last resort, redirect to Panel4All or a predefined URL
    setTimeout(function() {
        // If we're still here after a short delay, redirect
        window.location.href = 'https://panel4all.co.il';
    }, 300);
} 