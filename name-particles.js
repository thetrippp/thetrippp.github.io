(function () {
  const CONFIG = {
    words: ["RAGHAV", "GAME DEV", "SHADERS"],
    cycleInterval: 4800,   // ms each word stays fully formed before morphing to the next
    morphDuration: 900,    // ms the retarget/spawn/fade transition takes to feel settled

    fontFamily: "'Space Grotesk', sans-serif",
    fontSize: 100,
    fontWeight: "700",

    paddingX: 16,
    paddingY: 16,

    particleColor: "#f0f0f0",
    particleRadius: 1,
    sampleGap: 2,

    mouseRadius: 90,
    fleeStrength: 9,
    returnStiffness: 0.05,
    friction: 0.85
  };

  const slot = document.getElementById("nameContainer");
  const canvas = document.getElementById("particleCanvas");
  if (!slot || !canvas) return;
  const ctx = canvas.getContext("2d");

  let width = 0;
  let height = 0;
  let particles = [];
  let activeFontSize = CONFIG.fontSize;
  let wordIndex = 0;
  const mouse = { x: -9999, y: -9999 };

  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  canvas.addEventListener("mouseleave", () => {
    mouse.x = -9999;
    mouse.y = -9999;
  });

  class Particle {
    constructor(targetX, targetY, spawnNear) {
      this.targetX = targetX;
      this.targetY = targetY;
      if (spawnNear) {
        this.x = targetX + (Math.random() - 0.5) * 50;
        this.y = targetY + (Math.random() - 0.5) * 50;
      } else {
        this.x = targetX;
        this.y = targetY;
      }
      this.vx = 0;
      this.vy = 0;
      this.alpha = 1;
      this.dying = false;
    }

    update() {
      const dx = this.x - mouse.x;
      const dy = this.y - mouse.y;
      const dist = Math.hypot(dx, dy);
      let fleeX = 0;
      let fleeY = 0;

      if (dist < CONFIG.mouseRadius && dist > 0) {
        const force = (1 - dist / CONFIG.mouseRadius) * CONFIG.fleeStrength;
        fleeX = (dx / dist) * force;
        fleeY = (dy / dist) * force;
      }

      const homeDx = this.targetX - this.x;
      const homeDy = this.targetY - this.y;

      this.vx += fleeX + homeDx * CONFIG.returnStiffness;
      this.vy += fleeY + homeDy * CONFIG.returnStiffness;

      this.vx *= CONFIG.friction;
      this.vy *= CONFIG.friction;

      this.x += this.vx;
      this.y += this.vy;

      if (this.dying) {
        this.alpha -= 1 / (CONFIG.morphDuration / 16); // fade out over ~morphDuration
      }
    }

    draw(context) {
      if (this.alpha <= 0) return;
      context.globalAlpha = this.alpha;
      context.beginPath();
      context.arc(this.x, this.y, CONFIG.particleRadius, 0, Math.PI * 2);
      context.fill();
      context.globalAlpha = 1;
    }
  }

  // Measures a single font size that fits every configured word within
  // maxAllowedWidth, so all words render at the same size and the box is
  // sized once for the widest word rather than resizing per word.
  function computeSharedLayout() {
    const maxAllowedWidth = Math.min(slot.parentElement.clientWidth || window.innerWidth - 60, 900);
    let size = CONFIG.fontSize;

    const measureCanvas = document.createElement("canvas");
    const measureCtx = measureCanvas.getContext("2d");

    function widestWordWidthAt(fontSize) {
      measureCtx.font = `${CONFIG.fontWeight} ${fontSize}px ${CONFIG.fontFamily}`;
      let max = 0;
      CONFIG.words.forEach((w) => {
        const wid = measureCtx.measureText(w).width;
        if (wid > max) max = wid;
      });
      return max;
    }

    let widest = widestWordWidthAt(size);
    if (widest > maxAllowedWidth - CONFIG.paddingX * 2) {
      size = Math.floor(size * ((maxAllowedWidth - CONFIG.paddingX * 2) / widest));
      widest = widestWordWidthAt(size);
    }

    measureCtx.font = `${CONFIG.fontWeight} ${size}px ${CONFIG.fontFamily}`;
    const metrics = measureCtx.measureText(CONFIG.words[0]);
    const ascent = metrics.actualBoundingBoxAscent || size * 0.8;
    const descent = metrics.actualBoundingBoxDescent || size * 0.2;

    return {
      fontSize: size,
      ascent,
      descent,
      slotWidth: Math.ceil(widest + CONFIG.paddingX * 2),
      slotHeight: Math.ceil(ascent + descent + CONFIG.paddingY * 2)
    };
  }

  // Samples the particle target positions for one word, drawn at its own
  // natural width and right-aligned within the shared slot width — this is
  // what makes the box read as "pinned on the right, growing left" as words
  // change length, without the canvas itself needing fixed dimensions.
  function samplePoints(word, layout) {
    const measureCanvas = document.createElement("canvas");
    const measureCtx = measureCanvas.getContext("2d");
    measureCtx.font = `${CONFIG.fontWeight} ${layout.fontSize}px ${CONFIG.fontFamily}`;
    const wordWidth = measureCtx.measureText(word).width;

    const w = Math.ceil(wordWidth + CONFIG.paddingX * 2);
    const h = layout.slotHeight;

    const offscreen = document.createElement("canvas");
    const offCtx = offscreen.getContext("2d");
    offscreen.width = w;
    offscreen.height = h;

    offCtx.fillStyle = "#ffffff";
    offCtx.font = `${CONFIG.fontWeight} ${layout.fontSize}px ${CONFIG.fontFamily}`;
    offCtx.textAlign = "left";
    offCtx.textBaseline = "alphabetic";
    offCtx.fillText(word, CONFIG.paddingX, CONFIG.paddingY + layout.ascent);

    const imgData = offCtx.getImageData(0, 0, w, h).data;
    const points = [];
    for (let y = 0; y < h; y += CONFIG.sampleGap) {
      for (let x = 0; x < w; x += CONFIG.sampleGap) {
        const alphaIndex = (y * w + x) * 4 + 3;
        if (imgData[alphaIndex] > 128) points.push({ x, y });
      }
    }
    return { points, canvasWidth: w, canvasHeight: h };
  }

  // Resizes the canvas to this word's own width (right-aligned via CSS flex
  // on the slot) and reconciles the particle array with the new targets:
  // existing particles retarget in place (the morph), extra targets spawn
  // new particles, and surplus particles fade out instead of vanishing.
  function applyWord(word, layout, hardReset) {
    const sample = samplePoints(word, layout);
    width = sample.canvasWidth;
    height = sample.canvasHeight;

    canvas.width = width;
    canvas.height = height;
    slot.style.width = `${width}px`;
    slot.style.height = `${height}px`;

    if (hardReset) {
      particles = sample.points.map((p) => new Particle(p.x, p.y, true));
      return;
    }

    const alive = particles.filter((p) => !p.dying);
    const newPoints = sample.points;

    for (let i = 0; i < alive.length; i++) {
      if (i < newPoints.length) {
        alive[i].targetX = newPoints[i].x;
        alive[i].targetY = newPoints[i].y;
      } else {
        alive[i].dying = true; // surplus — fade out rather than snap away
      }
    }
    for (let i = alive.length; i < newPoints.length; i++) {
      particles.push(new Particle(newPoints[i].x, newPoints[i].y, true));
    }
  }

  function cycle() {
    wordIndex = (wordIndex + 1) % CONFIG.words.length;
    const layout = computeSharedLayout();
    applyWord(CONFIG.words[wordIndex], layout, false);
  }

  let cycleTimer = null;

  function init(hardReset) {
    const layout = computeSharedLayout();
    slot.parentElement.style.minWidth = `${layout.slotWidth}px`; // the fixed right-anchored slot
    applyWord(CONFIG.words[wordIndex], layout, hardReset);
  }

  window.addEventListener("resize", () => init(true));

  function loop() {
    // Clean up fully-faded particles so the array doesn't grow unbounded
    particles = particles.filter((p) => p.alpha > 0);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = CONFIG.particleColor;

    for (let i = 0; i < particles.length; i++) {
      particles[i].update();
      particles[i].draw(ctx);
    }

    requestAnimationFrame(loop);
  }

  init(true);
  loop();

  if (CONFIG.words.length > 1) {
    cycleTimer = setInterval(cycle, CONFIG.cycleInterval);
  }
})();
