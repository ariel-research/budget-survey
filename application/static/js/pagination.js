/**
 * Enhanced pagination experience for survey response tables
 * Provides keyboard navigation and loading states for pagination controls
 */
document.addEventListener('DOMContentLoaded', function() {
    // Add keyboard navigation for pagination
    document.addEventListener('keydown', function(e) {
        const paginationNav = document.querySelector('.pagination-nav');
        if (!paginationNav) return;
        
        // Find the correct previous and next links using stable data attributes
        const prevLink = paginationNav.querySelector('[data-pagination-role="previous"]');
        const nextLink = paginationNav.querySelector('[data-pagination-role="next"]');
        
        // Check if the parent item is disabled
        const isPrevDisabled = prevLink ? prevLink.closest('.page-item.disabled') : true;
        const isNextDisabled = nextLink ? nextLink.closest('.page-item.disabled') : true;
        
        // Previous page: Left arrow or P key
        if ((e.key === 'ArrowLeft' || e.key.toLowerCase() === 'p') && !isPrevDisabled && !e.target.matches('input, textarea, select')) {
            e.preventDefault();
            prevLink.click();
        }
        
        // Next page: Right arrow or N key
        if ((e.key === 'ArrowRight' || e.key.toLowerCase() === 'n') && !isNextDisabled && !e.target.matches('input, textarea, select')) {
            e.preventDefault();
            nextLink.click();
        }
    });
    
    // Add loading state when navigation links are clicked
    const paginationLinks = document.querySelectorAll('.pagination .page-item:not(.disabled) .page-link');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href') === '#') {
                e.preventDefault();
                return;
            }
            const nav = this.closest('.pagination-nav');
            if (nav) {
                nav.classList.add('loading');
            }
        });
    });
}); 