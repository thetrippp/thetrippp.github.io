function expandCard(card) {
    // Close any already expanded cards
    //const expandedCard = document.querySelector('.blog-card.expanded');
    //if (expandedCard && expandedCard !== card) {
    //    expandedCard.classList.remove('expanded');
    //}

    // Toggle expanded state on the clicked card
    card.classList.toggle('expanded');

    // Ensure content inside expanded card fills the space properly
    if (card.classList.contains('expanded')) {
        const content = card.querySelector('.blog-content');
        content.style.maxHeight = card.scrollHeight + "px"; // Adjust height dynamically
    }
}

// Close expanded card when clicking outside
document.addEventListener('click', (e) => {
    const expandedCard = document.querySelector('.blog-card.expanded');
    if (expandedCard && !expandedCard.contains(e.target)) {
        expandedCard.classList.remove('expanded');
    }
});
