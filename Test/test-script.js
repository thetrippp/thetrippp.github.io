const originalCardsMap = new Map();

function createCarousel(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!originalCardsMap.has(containerId)) {
        originalCardsMap.set(containerId, Array.from(container.children));
    }

    const cards = originalCardsMap.get(containerId);
    container.innerHTML = ''; 

    const width = window.innerWidth;
    let itemsPerPage;
    let columns;

    if (width < 600) {
        itemsPerPage = 3; 
        columns = "1fr";  
    } else if (width < 1024) {
        itemsPerPage = 4; 
        columns = "1fr 1fr"; 
    } else {
        itemsPerPage = 6; 
        columns = "1fr 1fr"; 
    }

    for (let i = 0; i < cards.length; i += itemsPerPage) {
        const page = document.createElement('div');
        page.className = 'page-container';
        page.style.width = "100%"; 
        page.style.gridTemplateColumns = columns;

        const chunk = cards.slice(i, i + itemsPerPage);
        chunk.forEach(card => {
            const clone = card.cloneNode(true);
            page.appendChild(clone);
        });
        
        container.appendChild(page);
    }

    // IMMEDIATELY update indicators after building the grid
    updateIndicatorVisibility(container);
}

// Call this after your createCarousel logic finishes rendering the cards
window.addEventListener('DOMContentLoaded', () => {
    // 1. Run your existing grid/card generation logic first
    const ids = ['experimentCarousel', 'projectCarousel'];
    ids.forEach(id => createCarousel(id));

    // 2. Initialize the "Smart" indicators
    initAllCarousels();
});

let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        const ids = ['experimentCarousel', 'projectCarousel'];
        ids.forEach(id => createCarousel(id));
    }, 200);
});
window.addEventListener('resize', () => {
    const viewports = document.querySelectorAll('.carousel-viewport');
    viewports.forEach(v => updateIndicatorVisibility(v));
});

function updateIndicators(containerId) {
    const container = document.getElementById(containerId);
    const leftHint = document.getElementById(`leftHint-${containerId}`);
    const rightHint = document.getElementById(`rightHint-${containerId}`);

    if (!container || !leftHint || !rightHint) return;

    const scrollLeft = container.scrollLeft;
    const maxScroll = container.scrollWidth - container.clientWidth;

    // Show left hint if we've scrolled right at all
    if (scrollLeft > 10) {
        leftHint.classList.add('is-visible');
    } else {
        leftHint.classList.remove('is-visible');
    }

    // Show right hint if there is more content to the right
    // We use -10 as a buffer for browser rounding issues
    if (scrollLeft < maxScroll - 10) {
        rightHint.classList.add('is-visible');
    } else {
        rightHint.classList.remove('is-visible');
    }
}

function updateIndicatorVisibility(viewport) {
    const section = viewport.closest('.carousel-section');
    if (!section) return;

    const leftHint = section.querySelector('.left-hint');
    const rightHint = section.querySelector('.right-hint');

    const scrollLeft = viewport.scrollLeft;
    // We use Math.ceil to prevent sub-pixel rounding errors on high-DPI screens
    const maxScroll = viewport.scrollWidth - viewport.clientWidth;

    if (leftHint) {
        scrollLeft > 10 ? leftHint.classList.add('is-visible') : leftHint.classList.remove('is-visible');
    }

    if (rightHint) {
        // Only show if there is meaningful content to scroll to (> 10px)
        maxScroll > 10 && scrollLeft < (maxScroll - 10) 
            ? rightHint.classList.add('is-visible') 
            : rightHint.classList.remove('is-visible');
    }
}

function initAllCarousels() {
    const viewports = document.querySelectorAll('.carousel-viewport');
    
    viewports.forEach(viewport => {
        // Run once on load to set initial arrow state
        // Wrapped in timeout to allow layout to settle
        setTimeout(() => updateIndicatorVisibility(viewport), 100);

        // Update arrows whenever the user scrolls this specific viewport
        viewport.addEventListener('scroll', () => {
            updateIndicatorVisibility(viewport);
        });
    });
}

// Update your initialization to listen for scrolls
window.addEventListener('DOMContentLoaded', () => {
    const ids = ['experimentCarousel', 'projectCarousel'];
    ids.forEach(id => {
        createCarousel(id);
        const container = document.getElementById(id);
        if (container) {
            container.addEventListener('scroll', () => updateIndicatorVisibility(container));
        }
    });
});

