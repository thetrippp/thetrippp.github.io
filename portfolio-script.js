// Animate skill bars when the panel scrolls into view
const skillsPanel = document.querySelector('.skills-panel');

if (skillsPanel) {
    const observer = new IntersectionObserver(
        ([entry]) => {
            if (entry.isIntersecting) {
                skillsPanel.classList.add('in-view');
                observer.disconnect();
            }
        },
        { threshold: 0.3 }
    );
    observer.observe(skillsPanel);
}
