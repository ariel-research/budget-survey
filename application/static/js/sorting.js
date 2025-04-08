document.addEventListener('DOMContentLoaded', function() {
    // Find all sortable headers
    const sortableHeaders = document.querySelectorAll('th.sortable');
    
    // Find all headers with class "sortable" and run this function for each one
    sortableHeaders.forEach(header => {
        
        // When someone clicks on a sortable header:
        header.addEventListener('click', function() {
            // Get which field we're sorting by from data-sort attribute
            const sortBy = this.dataset.sort;
            
            // Get current sort order from data-order attribute, default to 'asc' if not set
            const currentOrder = this.dataset.order || 'asc';
            
            // Toggle the sort order (if ascending, change to descending and vice versa)
            const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
            
            // Create a URL object based on current page
            const url = new URL(window.location);
            
            // Add or update sort parameters in the URL
            url.searchParams.set('sort', sortBy);
            url.searchParams.set('order', newOrder);
            
            // Navigate to the new URL with sort parameters
            window.location.href = url.toString();
        });
        
        // AFTER setting up the click event, check if this column is currently being sorted
        
        // Get current sort values from URL
        const sortBy = new URLSearchParams(window.location.search).get('sort');
        const sortOrder = new URLSearchParams(window.location.search).get('order');
        
        // If this header matches the current sort field
        if (sortBy === header.dataset.sort) {
            // Add a "sorted" class to highlight it
            header.classList.add('sorted');
            
            // Store the sort order on the element
            header.dataset.order = sortOrder;
            
            // Create an arrow indicator (↑ or ↓)
            const indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.textContent = sortOrder === 'asc' ? ' ↑' : ' ↓';
            
            // Add the arrow indicator to the header
            header.appendChild(indicator);
        }
    });
});