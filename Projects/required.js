document.addEventListener("scroll", function () {
    let button = document.querySelector(".floating-button");
    let scrollPosition = window.scrollY;
    let maxFadeDistance = 40; // Adjust how far the fade effect lasts

    // Calculate opacity based on scroll position (fades out over 300px)
    let opacity = Math.max(1 - scrollPosition / maxFadeDistance, 0);
    button.style.opacity = opacity;
});
