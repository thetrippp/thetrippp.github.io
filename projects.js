(function () {
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : str;
    return div.innerHTML;
  }

  function isFeatured(row) {
    return (row.featured || '').trim().toLowerCase() === 'yes';
  }

  function isComingSoon(row) {
    return (row.status || '').trim() === 'coming-soon';
  }

  function splitList(str) {
    return (str || '').split(';').map(function (s) { return s.trim(); }).filter(Boolean);
  }

  function buildFeaturedCard(row) {
    return (
      '<div class="featured-media" style="background-image:url(\'' + escapeHtml(row.image) + '\')"></div>\n' +
      '      <div class="featured-body">\n' +
      (row.venue ? '        <span class="featured-badge">' + escapeHtml(row.venue) + '</span>\n' : '') +
      '        <h2 class="featured-title">' + escapeHtml(row.title) + '</h2>\n' +
      '        <p class="featured-summary">' + escapeHtml(row.summary) + '</p>\n' +
      (row.link ? '        <a href="' + escapeHtml(row.link) + '" class="featured-cta">' + escapeHtml(row.cta_text || 'View Full Write-Up →') + '</a>\n' : '') +
      '      </div>'
    );
  }

  // Each row renders once per clone index (0 = real set, 1/2 = loop clones) so
  // aria-hidden can be set on the duplicates without touching real content.
  function buildCarouselCard(row, cloneIndex) {
    var comingSoon = isComingSoon(row);
    var cardClass = 'carousel-card' + (comingSoon ? ' coming-soon' : '');
    var isClone = cloneIndex !== 1;
    var ariaHidden = isClone ? ' aria-hidden="true"' : '';
    // aria-hidden only hides clones from screen readers — it does not block
    // pointer/touch clicks. The viewport shows several cards at once, and
    // wrap-correction only guarantees the single leftmost-ish card is real;
    // cards further right in the same view can still be clones. Every
    // duplicate is the same project with the same link, so all of them stay
    // clickable regardless of which physical copy happens to be on screen.
    var linkOverlay = (!comingSoon && row.link)
      ? '<a href="' + escapeHtml(row.link) + '" class="card-link-overlay" aria-label="' + escapeHtml(row.title) + ' project" target="_blank"></a>\n        '
      : '';

    var tags = splitList(row.tags).slice(0, 3);
    var tagsHtml = tags.length
      ? '          <div class="carousel-card-tags">' + tags.map(function (t) {
        return '<span class="carousel-card-tag">' + escapeHtml(t) + '</span>';
      }).join('') + '</div>\n'
      : '';

    var skills = splitList(row.skills);
    var skillsHtml = skills.length
      ? '          <p class="carousel-card-skills">' + escapeHtml(skills.join(' · ')) + '</p>\n'
      : '';

    return (
      '<article class="' + cardClass + '"' + ariaHidden + ' data-project-title="' + escapeHtml(row.title) + '">\n' +
      '        ' + linkOverlay +
      '<div class="card-media" style="background-image:url(\'' + escapeHtml(row.image) + '\')"></div>\n' +
      '        <div class="carousel-card-body">\n' +
      tagsHtml +
      '          <h3 class="carousel-card-title">' + escapeHtml(row.title) + '</h3>\n' +
      '          <p class="carousel-card-summary">' + escapeHtml(row.summary) + '</p>\n' +
      skillsHtml +
      (comingSoon ? '' : '          <span class="carousel-card-cta">' + escapeHtml(row.cta_text || 'View Project →') + '</span>\n') +
      '        </div>\n' +
      '      </article>'
    );
  }

  function render(rows) {
    var featuredContainer = document.getElementById('featured-project');
    var track = document.getElementById('carousel-track');
    if (!featuredContainer || !track) return;

    var featuredRow = rows.filter(isFeatured)[0];
    var restRows = rows.filter(function (r) { return r !== featuredRow; });

    if (featuredRow) {
      featuredContainer.innerHTML = buildFeaturedCard(featuredRow);
    } else {
      console.warn('No row in projects.csv has featured=yes; pinned slot left empty.');
    }

    if (restRows.length === 0) return;

    // Render the real set plus one clone set on each side so there's always
    // more track to scroll into — the illusion of an infinite loop.
    var perSet = restRows.length;
    var sets = [0, 1, 2].map(function (cloneIndex) {
      return restRows.map(function (row) { return buildCarouselCard(row, cloneIndex); }).join('\n\n      ');
    });
    track.innerHTML = sets.join('\n\n      ');

    requestAnimationFrame(function () {
      track.querySelectorAll('.carousel-card').forEach(function (card) {
        card.classList.add('is-visible');
      });
      var loopControl = initLoop(track, perSet);
      wireViewportInteractions(loopControl);
    });
  }

  function renderError() {
    var track = document.getElementById('carousel-track');
    if (track) {
      track.innerHTML = '<p style="color: var(--text-muted);">Couldn\'t load projects right now — check that projects.csv is reachable.</p>';
    }
  }

  // Keeps the scroll position inside the middle (real) set. When the
  // *nearest/leading* card belongs to a clone set rather than the real one,
  // silently jump by one set-width so the real equivalent becomes nearest
  // instead — invisible to the eye since the clone looks identical.
  //
  // This checks which card is actually nearest, not just whether scrollLeft
  // has crossed a raw w/2w boundary. Those aren't the same thing: the
  // nearest/leading card (the one people perceive as active and click) can
  // already be a clone before scrollLeft technically crosses that boundary
  // — there's a roughly half-card dead zone near each edge where a boundary
  // check says "still fine" while the clickable overlay has already handed
  // off to a non-interactive clone card.
  function initLoop(track, perSet) {
    var viewport = track.parentElement;
    var cards = Array.prototype.slice.call(track.children);
    if (cards.length < perSet * 3) return null;

    function setWidth() {
      return cards[perSet].offsetLeft - cards[0].offsetLeft;
    }

    function nearestCloneSet() {
      var bestDist = Infinity, bestIdx = -1;
      for (var i = 0; i < cards.length; i++) {
        var d = Math.abs(cards[i].offsetLeft - viewport.scrollLeft);
        if (d < bestDist) { bestDist = d; bestIdx = i; }
      }
      return Math.floor(bestIdx / perSet); // 0 = left clone, 1 = real, 2 = right clone
    }

    var width = setWidth();
    viewport.scrollLeft = width; // start at the beginning of the middle (real) set

    var suppressLiveCorrection = false;

    function correct() {
      var w = setWidth();
      if (w <= 0) return;
      var cloneSet = nearestCloneSet();
      if (cloneSet === 0) {
        viewport.scrollLeft += w;
      } else if (cloneSet === 2) {
        viewport.scrollLeft -= w;
      }
    }

    viewport.addEventListener('scroll', function () {
      // While a manual scrollByCards() animation is running, it owns
      // scrollLeft for that duration — correcting mid-animation is what
      // caused the native-smooth-scroll conflict (fine going forward,
      // broke going backward). Only auto-correct for wheel/drag scrolling,
      // which isn't animated and has no such conflict.
      if (suppressLiveCorrection) return;
      correct();
    });

    window.addEventListener('resize', function () {
      // Recompute and recenter on the real set; a minor reset on resize,
      // rather than trying to preserve the exact scroll offset across a
      // width change.
      viewport.scrollLeft = setWidth();
    });

    return {
      correct: correct,
      setSuppressed: function (value) { suppressLiveCorrection = value; }
    };
  }

  // A self-owned smooth-scroll animation, used instead of the browser's
  // native scrollBy({behavior:'smooth'}) — native smooth-scroll can't be
  // safely interrupted mid-flight, which is what broke wrapping in one
  // direction. This version fully controls scrollLeft every frame and
  // resolves cleanly when done, so the wrap correction can run exactly once,
  // after the animation, with no fight over who owns the position.
  //
  // A shared token guards against a second animation starting before the
  // first finishes (e.g. clicking the arrow faster than the animation
  // duration). Without this, two rAF loops would both write to scrollLeft
  // on the same frames, and whichever one happened to finish first would
  // fire the wrap-correction against a position the other loop had already
  // moved past — drifting scrollLeft into clone territory over repeated
  // rapid clicks, which is what made cards stop being clickable.
  var activeScrollToken = 0;

  function animateScrollBy(viewport, delta, duration, loopControl) {
    var myToken = ++activeScrollToken;
    if (loopControl) loopControl.setSuppressed(true);
    var start = viewport.scrollLeft;
    var startTime = null;

    function step(ts) {
      if (myToken !== activeScrollToken) return; // superseded by a newer click; abandon this loop
      if (startTime === null) startTime = ts;
      var t = Math.min((ts - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      viewport.scrollLeft = start + delta * eased;
      if (t < 1) {
        requestAnimationFrame(step);
      } else if (loopControl) {
        loopControl.setSuppressed(false);
        loopControl.correct();
      }
    }
    requestAnimationFrame(step);
  }

  // Hands control back to live/direct scrolling by invalidating any in-flight
  // button/auto-rotate animation (its step() self-aborts on the next frame)
  // and re-enabling the live wrap-correction. Must be called before wheel or
  // drag scrolling touches scrollLeft directly, or an animation still
  // writing to scrollLeft every frame will fight it and drift position into
  // clone territory — the same conflict class as overlapping button clicks,
  // just between a different pair of input methods.
  function cancelAnimation(loopControl) {
    activeScrollToken++;
    if (loopControl) loopControl.setSuppressed(false);
  }

  function wireViewportInteractions(loopControl) {
    var viewport = document.querySelector('.carousel-viewport');
    var prevBtn = document.getElementById('carousel-prev');
    var nextBtn = document.getElementById('carousel-next');
    if (!viewport) return;

    function scrollByCard(direction) {
      var card = viewport.querySelector('.carousel-card');
      var step = card ? card.getBoundingClientRect().width + 18 : 340;
      animateScrollBy(viewport, direction * step, 380, loopControl);
    }

    if (prevBtn) prevBtn.addEventListener('click', function () { scrollByCard(-1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { scrollByCard(1); });

    // Translate vertical mouse-wheel input into horizontal scroll — a plain
    // wheel event only carries deltaY, and overflow-x:auto alone does not
    // respond to it, which is why the carousel felt unscrollable by mouse.
    viewport.addEventListener('wheel', function (e) {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        cancelAnimation(loopControl);
        viewport.scrollLeft += e.deltaY;
      }
    }, { passive: false });

    // A drag/touch scroll fires native 'scroll' events directly — same
    // conflict risk if a button animation is still running when it starts.
    viewport.addEventListener('pointerdown', function () { cancelAnimation(loopControl); });
    viewport.addEventListener('touchstart', function () { cancelAnimation(loopControl); }, { passive: true });

    setupAutoRotate(viewport, prevBtn, nextBtn, scrollByCard);
  }

  // Auto-advances one card at a time after a period with no interaction.
  // Any scroll, click, drag, or hover resets the idle countdown so it never
  // fights the person actually browsing.
  function setupAutoRotate(viewport, prevBtn, nextBtn, scrollByCard) {
    var IDLE_DELAY = 3000;   // ms of no interaction before auto-rotation starts
    var STEP_INTERVAL = 2000; // ms between automatic advances once idle
    var idleTimer = null;
    var autoTimer = null;

    function stopAuto() {
      if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    }

    function startAuto() {
      stopAuto();
      autoTimer = setInterval(function () { scrollByCard(1); }, STEP_INTERVAL);
    }

    function resetIdle() {
      stopAuto();
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(startAuto, IDLE_DELAY);
    }

    ['wheel', 'pointerdown', 'touchstart'].forEach(function (evt) {
      viewport.addEventListener(evt, resetIdle, { passive: true });
    });
    viewport.addEventListener('mouseenter', function () {
      stopAuto();
      if (idleTimer) clearTimeout(idleTimer);
    });
    viewport.addEventListener('mouseleave', resetIdle);
    if (prevBtn) prevBtn.addEventListener('click', resetIdle);
    if (nextBtn) nextBtn.addEventListener('click', resetIdle);

    resetIdle(); // start the idle countdown as soon as the carousel is ready
  }

  fetch('projects.csv')
    .then(function (res) {
      if (!res.ok) throw new Error('CSV fetch failed: ' + res.status);
      return res.text();
    })
    .then(function (csvText) {
      var parsed = Papa.parse(csvText, { header: true, skipEmptyLines: true });
      if (parsed.errors && parsed.errors.length) {
        console.warn('projects.csv parse warnings:', parsed.errors);
      }
      render(parsed.data);
    })
    .catch(function (err) {
      console.error(err);
      renderError();
    });
})();
