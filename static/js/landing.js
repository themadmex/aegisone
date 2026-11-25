/* AegisOne Open — Landing Page Interactive Controller
   1. Sticky liquid-glass navbar & mobile drawer
   2. Soft full-width Hero Scroll Parallax + Rising Curtain reveal
   3. Interactive 21 Questions switcher (Q02 Email MFA & Q21 "50 Cent Check")
   4. Section 2 animated baseline score counter + offscreen animation pause
   5. 5-plate isometric core spring explosion, cursor spotlight, & connector beads */

(() => {
  const reducedQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduceMotion = reducedQuery.matches;

  if (!reduceMotion && 'IntersectionObserver' in window) {
    const revealEls = Array.from(document.querySelectorAll('.reveal'));
    if (revealEls.length) {
      document.documentElement.classList.add('has-reveal');
      const revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-revealed');
              revealObserver.unobserve(entry.target);
            }
          });
        },
        { rootMargin: '0px 0px 48px 0px', threshold: 0.01 }
      );
      revealEls.forEach((el) => revealObserver.observe(el));
    }
  }

  // ---------- 1. Sticky Navbar & Mobile Menu ----------
  const root = document.querySelector('.n3-root');
  const header = document.getElementById('n3-header');
  const navBar = document.getElementById('n3-nav-bar');
  const menuBtn = document.getElementById('n3-menu-btn');
  const mobileMenu = document.getElementById('n3-mobile-menu');

  // ---------- 2. Damped Hero Depth Parallax & Smooth Anchor Glide ----------
  const heroSection = document.getElementById('top');
  const heroVisualCol = document.querySelector('.n3-visual-col');
  const floorWrap = document.getElementById('n3-floor-wrap');

  let menuOpen = false;
  let pageScrolled = false;
  let targetScrollY = window.scrollY || 0;
  let smoothScrollY = targetScrollY;
  let parallaxRaf = 0;

  const syncNavBar = () => {
    if (!navBar) return;
    navBar.classList.toggle('n3-nav-bar-scrolled', pageScrolled || menuOpen);
  };

  const resetHeroParallax = () => {
    if (heroVisualCol) heroVisualCol.style.transform = '';
    if (floorWrap) floorWrap.style.transform = '';
  };

  const tickHeroParallax = () => {
    parallaxRaf = 0;
    if (!heroVisualCol || !heroSection || reduceMotion || window.innerWidth < 1024) {
      resetHeroParallax();
      return;
    }

    const diff = targetScrollY - smoothScrollY;
    if (Math.abs(diff) > 0.2) {
      smoothScrollY += diff * 0.14;
      parallaxRaf = requestAnimationFrame(tickHeroParallax);
    } else {
      smoothScrollY = targetScrollY;
    }

    const clamped = Math.min(Math.max(smoothScrollY, 0), 700);
    const visualY = clamped * 0.08;
    const floorY = clamped * 0.045;
    heroVisualCol.style.transform = `translate3d(0, ${visualY.toFixed(2)}px, 0)`;
    if (floorWrap) {
      floorWrap.style.transform = `translate3d(0, ${floorY.toFixed(2)}px, 0)`;
    }
  };

  const onScroll = () => {
    const sy = window.scrollY || 0;
    targetScrollY = sy;
    const nextScrolled = sy > 12;
    if (nextScrolled !== pageScrolled) {
      pageScrolled = nextScrolled;
      syncNavBar();
    }
    if (!reduceMotion && window.innerWidth >= 1024 && !parallaxRaf) {
      parallaxRaf = requestAnimationFrame(tickHeroParallax);
    }
  };

  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', () => {
    if (window.innerWidth < 1024 || reduceMotion) {
      resetHeroParallax();
    } else if (!parallaxRaf) {
      parallaxRaf = requestAnimationFrame(tickHeroParallax);
    }
  }, { passive: true });

  // Silky eased in-page anchor scrolling (#how-it-works, #inside, #approach, #pilot)
  let anchorRaf = 0;
  const cancelAnchorScroll = () => {
    if (anchorRaf) {
      cancelAnimationFrame(anchorRaf);
      anchorRaf = 0;
    }
  };
  window.addEventListener('wheel', cancelAnchorScroll, { passive: true });
  window.addEventListener('touchstart', cancelAnchorScroll, { passive: true });

  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const href = anchor.getAttribute('href');
      if (!href || href === '#') return;
      const target = document.querySelector(href);
      if (!target) return;

      e.preventDefault();
      cancelAnchorScroll();

      // Pre-reveal target elements so there is zero fade-in lag on arrival
      target.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-revealed'));
      if (target.classList.contains('reveal')) target.classList.add('is-revealed');

      const navOffset = header ? header.offsetHeight - 8 : 68;
      const startY = window.scrollY || 0;
      const rawDest = startY + target.getBoundingClientRect().top - (href === '#main' || href === '#top' ? 0 : navOffset);
      const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      const destY = Math.max(0, Math.min(rawDest, maxScroll));
      const distance = destY - startY;

      if (reduceMotion || Math.abs(distance) < 4) {
        window.scrollTo(0, destY);
        history.replaceState(null, '', href);
        return;
      }

      const duration = Math.min(760, Math.max(460, Math.abs(distance) * 0.45));
      const startTime = performance.now();
      const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

      const stepScroll = (now) => {
        const elapsed = now - startTime;
        const t = Math.min(1, elapsed / duration);
        window.scrollTo(0, startY + distance * easeInOutCubic(t));
        if (t < 1) {
          anchorRaf = requestAnimationFrame(stepScroll);
        } else {
          anchorRaf = 0;
          history.replaceState(null, '', href);
        }
      };
      anchorRaf = requestAnimationFrame(stepScroll);
    });
  });

  if (header && root) {
    const measureNav = () => {
      if (!menuOpen) {
        root.style.setProperty('--n3-nav-space', `${header.offsetHeight}px`);
      }
    };
    measureNav();
    window.addEventListener('resize', measureNav, { passive: true });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measureNav);
    }
  }

  const setMenuOpen = (next) => {
    menuOpen = next;
    if (!menuBtn || !mobileMenu) return;
    menuBtn.setAttribute('aria-expanded', String(menuOpen));
    menuBtn.setAttribute('aria-label', menuOpen ? 'Close menu' : 'Open menu');
    mobileMenu.hidden = !menuOpen;
    const openIcon = menuBtn.querySelector('[data-menu-icon="open"]');
    const closeIcon = menuBtn.querySelector('[data-menu-icon="close"]');
    if (openIcon) openIcon.hidden = menuOpen;
    if (closeIcon) closeIcon.hidden = !menuOpen;
    syncNavBar();
  };

  if (menuBtn) {
    menuBtn.addEventListener('click', () => setMenuOpen(!menuOpen));
  }

  if (mobileMenu) {
    mobileMenu.querySelectorAll('[data-mobile-link]').forEach((link) => {
      link.addEventListener('click', () => setMenuOpen(false));
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menuOpen) {
      setMenuOpen(false);
      if (menuBtn) menuBtn.focus();
    }
  });

  // ---------- 3. Interactive 21 Questions Switcher (Q02 & Q21 Joke) ----------
  const DEMO_QUESTIONS = {
    q02: {
      prompt: 'Does everyone use two-step verification (MFA) on company email accounts?',
      help: 'An authenticator app or security key stops a stolen password from opening a staff inbox.',
      subs: { yes: 'Every mailbox', partly: 'Some accounts', no: 'Passwords only', unsure: 'Need to check' },
      defaultChoice: 'partly',
      outcomes: {
        yes: {
          tone: 'ok',
          chipClass: 'lp-chip lp-chip-teal',
          badge: 'In place · +2 baseline pts',
          rule: 'Rule Q02 → Passing',
          title: 'Recorded in your baseline — no action created',
          desc: 'Great coverage. AegisOne logs your answer in your dated report and keeps your action plan focused on genuine gaps.',
        },
        partly: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'High priority · +1 baseline pt',
          rule: 'Rule Q02 → Action',
          title: 'Require MFA for remaining staff email accounts',
          desc: 'Enforce two-step sign-in across your email admin console and verify the completion list so shared or forgotten inboxes aren’t left exposed.',
        },
        no: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'High priority · +0 baseline pts',
          rule: 'Rule Q02 → Action',
          title: 'Turn on MFA across company email, starting with admins & finance',
          desc: 'Ranks near the top of your plan with step-by-step setup notes and a simple check to confirm every active mailbox is enrolled.',
        },
        unsure: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'Verify first · +0 baseline pts',
          rule: 'Rule Q02 → Check',
          title: 'Check MFA status in your email provider’s user list',
          desc: 'You never have to guess. Marking “Unsure” creates a 3-minute verification step you can check yourself or assign to your IT contact.',
        },
      },
    },
    q21: {
      prompt: 'Question 21: If your main work laptop fell off tomorrow, would your backups still love you?',
      help: 'Apologies to 50 Cent — in plain English, if a laptop vanished in a taxi tonight, could you lock it remotely and carry on without panic?',
      subs: { yes: 'Still loyal', partly: 'Files, maybe', no: 'Heartbreak', unsure: 'Let’s find out' },
      defaultChoice: 'unsure',
      outcomes: {
        yes: {
          tone: 'ok',
          chipClass: 'lp-chip lp-chip-teal',
          badge: 'True devotion · +2 baseline pts',
          rule: 'Rule Q21 → Passing',
          title: 'Nate Dogg would be proud — logged in your baseline',
          desc: 'Remote sign-out works and your backups restore cleanly. A missing laptop is an inconvenience, not a lost week.',
        },
        partly: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'Worth testing · +1 baseline pt',
          rule: 'Rule Q21 → Action',
          title: 'Run a 10-minute lost-laptop & restore dry run',
          desc: 'Cloud sync helps, but verify you can remotely revoke active sessions and restore key business files onto a spare machine.',
        },
        no: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'Breakup territory · +0 baseline pts',
          rule: 'Rule Q21 → Action',
          title: 'Set up remote session sign-out and automatic cloud/offsite backup',
          desc: 'Adds a practical checklist so one misplaced laptop in a cab doesn’t take client work or saved credentials with it.',
        },
        unsure: {
          tone: 'priority',
          chipClass: 'lp-chip lp-chip-pop',
          badge: 'Verify first · +0 baseline pts',
          rule: 'Rule Q21 → Check',
          title: 'Walk through “what happens in hour one if a laptop vanishes?”',
          desc: 'Most teams haven’t tested this until it happens. AegisOne adds a calm, 10-minute dry run you can do with your IT contact.',
        },
      },
    },
  };

  let currentQKey = 'q02';
  let currentChoiceKey = 'partly';

  const qTabs = Array.from(document.querySelectorAll('[data-q-tab]'));
  const choiceBtns = Array.from(document.querySelectorAll('[data-demo-choice]'));
  const demoQLabel = document.getElementById('demo-q-label');
  const demoQHelp = document.getElementById('demo-q-help');
  const demoSubYes = document.getElementById('demo-sub-yes');
  const demoSubPartly = document.getElementById('demo-sub-partly');
  const demoSubNo = document.getElementById('demo-sub-no');
  const demoSubUnsure = document.getElementById('demo-sub-unsure');
  const demoOutcome = document.getElementById('demo-outcome');
  const demoBadge = document.getElementById('demo-badge');
  const demoRule = document.getElementById('demo-rule');
  const demoTitle = document.getElementById('demo-title');
  const demoDesc = document.getElementById('demo-desc');

  const renderDemo = (focusChoice = false) => {
    const q = DEMO_QUESTIONS[currentQKey];
    if (!q) return;
    const data = q.outcomes[currentChoiceKey];
    if (!data) return;

    qTabs.forEach((tab) => {
      const active = tab.getAttribute('data-q-tab') === currentQKey;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-pressed', String(active));
    });

    if (demoQLabel) demoQLabel.textContent = q.prompt;
    if (demoQHelp) demoQHelp.textContent = q.help;
    if (demoSubYes) demoSubYes.textContent = q.subs.yes;
    if (demoSubPartly) demoSubPartly.textContent = q.subs.partly;
    if (demoSubNo) demoSubNo.textContent = q.subs.no;
    if (demoSubUnsure) demoSubUnsure.textContent = q.subs.unsure;

    choiceBtns.forEach((btn) => {
      const active = btn.getAttribute('data-demo-choice') === currentChoiceKey;
      btn.classList.toggle('is-selected', active);
      btn.setAttribute('aria-checked', String(active));
      btn.tabIndex = active ? 0 : -1;
      if (active && focusChoice) btn.focus();
    });

    if (demoOutcome) demoOutcome.setAttribute('data-tone', data.tone);
    if (demoBadge) {
      demoBadge.className = data.chipClass;
      demoBadge.textContent = data.badge;
    }
    if (demoRule) demoRule.textContent = data.rule;
    if (demoTitle) demoTitle.textContent = data.title;
    if (demoDesc) demoDesc.textContent = data.desc;
  };

  qTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const nextQ = tab.getAttribute('data-q-tab');
      if (!DEMO_QUESTIONS[nextQ] || nextQ === currentQKey) return;
      currentQKey = nextQ;
      currentChoiceKey = DEMO_QUESTIONS[nextQ].defaultChoice;
      renderDemo(false);
    });
  });

  if (choiceBtns.length) {
    choiceBtns.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        currentChoiceKey = btn.getAttribute('data-demo-choice') || 'partly';
        renderDemo(false);
      });
      btn.addEventListener('keydown', (e) => {
        if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(e.key)) return;
        e.preventDefault();
        const delta = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : -1;
        const nextIdx = (idx + delta + choiceBtns.length) % choiceBtns.length;
        currentChoiceKey = choiceBtns[nextIdx].getAttribute('data-demo-choice') || 'partly';
        renderDemo(true);
      });
    });
  }

  // ---------- 4. Section 2 Animated Platform Bento (Score Sweep + Visibility Pause) ----------
  const platformBento = document.getElementById('lp-platform-bento');
  const scoreArc = document.getElementById('lp-score-arc');
  const scoreNum = document.getElementById('lp-score-num');
  let scoreAnimated = false;

  const animateScoreGauge = () => {
    if (scoreAnimated || !scoreArc || !scoreNum) return;
    scoreAnimated = true;
    if (reduceMotion) {
      scoreArc.setAttribute('stroke-dashoffset', '44.2');
      scoreNum.textContent = '68%';
      return;
    }
    scoreArc.setAttribute('stroke-dashoffset', '138.2');
    scoreNum.textContent = '0%';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        scoreArc.setAttribute('stroke-dashoffset', '44.2');
      });
    });
    const start = performance.now();
    const dur = 1100;
    const stepNum = (now) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      scoreNum.textContent = `${Math.round(eased * 68)}%`;
      if (t < 1) requestAnimationFrame(stepNum);
    };
    requestAnimationFrame(stepNum);
  };

  if (platformBento && 'IntersectionObserver' in window) {
    const bentoObserver = new IntersectionObserver(
      ([entry]) => {
        platformBento.classList.toggle('is-offscreen', !entry.isIntersecting);
        if (entry.isIntersecting) animateScoreGauge();
      },
      { rootMargin: '60px' }
    );
    bentoObserver.observe(platformBento);
  }

  // ---------- 5. Hero Floor Cursor Spotlight ----------
  const floorSpot = document.getElementById('n3-floor-spot');
  const floorLit = document.getElementById('n3-floor-lit');
  const SPOT_SIZE = 340;

  if (heroSection && floorWrap && floorSpot && floorLit) {
    if ('ResizeObserver' in window) {
      const floorResize = new ResizeObserver(([entry]) => {
        floorLit.style.width = `${entry.contentRect.width}px`;
        floorLit.style.height = `${entry.contentRect.height}px`;
      });
      floorResize.observe(heroSection);
    }

    let spotFrame = 0;

    heroSection.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse' || reduceMotion) return;
      cancelAnimationFrame(spotFrame);
      spotFrame = requestAnimationFrame(() => {
        const box = heroSection.getBoundingClientRect();
        const x = e.clientX - box.left - SPOT_SIZE / 2;
        const y = e.clientY - box.top - SPOT_SIZE / 2;
        floorSpot.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
        floorLit.style.transform = `translate3d(${(-x).toFixed(1)}px, ${(-y).toFixed(1)}px, 0)`;
        floorWrap.dataset.spot = 'on';
      });
    });

    heroSection.addEventListener('pointerleave', () => {
      cancelAnimationFrame(spotFrame);
      floorWrap.dataset.spot = 'off';
    });
  }

  // ---------- 6. Core Visual Spring Physics & 5-Plate Explosion ----------
  const visual = document.getElementById('n3-visual');
  if (!visual) return;

  const coreTrigger = document.getElementById('n3-core-trigger');
  const restCore = document.getElementById('n3-rest-core');
  const explodedCore = document.getElementById('n3-exploded-core');
  const shadowLayer = document.getElementById('n3-shadow-layer');
  const hint = document.getElementById('n3-hint');
  const connectorsWrap = visual.querySelector('[data-connectors]');
  const stageCardsList = visual.querySelector('[data-stage-cards]');

  const parallaxLayers = Array.from(visual.querySelectorAll('[data-parallax]')).map((el) => ({
    el,
    reach: Number(el.getAttribute('data-parallax')) || 0,
  }));
  const orbitGroups = Array.from(visual.querySelectorAll('[data-orbit-group]'));
  const tiltedLayers = Array.from(visual.querySelectorAll('[data-tilted]'));
  const particleSvgs = Array.from(visual.querySelectorAll('[data-particles]'));

  const TILT_DEGREES = 3.5;
  const ORBIT_OPEN_OPACITY = 0.15;
  const AI_PLATE = 2;
  const STAGGER = 0.05;
  const TRAVEL = [114, 37, -32, -107, -194];
  const SCALES = [0.63, 0.62, 0.7, 1.07, 1.06];
  const SIDES = ['right', 'left', 'right', 'left', 'right'];
  const REST_INSET = 10;
  const OUTWARD = 2;
  const BEAD_SECONDS = 1.6;
  const BEAD_REPEAT_DELAY = 1.4;

  const plates = [0, 1, 2, 3, 4].map((i) => {
    const g = visual.querySelector(`[data-plate="${i}"]`);
    return {
      g,
      cy: g ? Number(g.getAttribute('data-cy')) : 450,
      shadow: visual.querySelector(`[data-plate-shadow="${i}"]`),
      skirt: visual.querySelector(`[data-plate-skirt="${i}"]`),
    };
  });

  const strongGlow = visual.querySelector('[data-strong-glow]');
  const aiSpill = visual.querySelector('[data-ai-spill]');
  const aiRim = visual.querySelector('[data-ai-rim]');
  const aiHalo = visual.querySelector('[data-ai-halo]');
  const aiCore = visual.querySelector('[data-ai-core]');

  const stageCards = [0, 1, 2, 3, 4].map((i) => visual.querySelector(`[data-stage-card="${i}"]`));
  const connectors = [0, 1, 2, 3, 4].map((i) => {
    const svg = visual.querySelector(`[data-connector="${i}"]`);
    return {
      svg,
      plateX: svg ? Number(svg.getAttribute('data-plate-x')) : 500,
      nodeX: svg ? Number(svg.getAttribute('data-node-x')) : 500,
      lit: visual.querySelector(`[data-conn-lit="${i}"]`),
      halo: visual.querySelector(`[data-conn-halo="${i}"]`),
      bead: visual.querySelector(`[data-conn-bead="${i}"]`),
    };
  });

  const clamp01 = (v) => Math.min(1, Math.max(0, v));
  const mapRange = (v, inMin, inMax, outMin, outMax) => {
    const t = clamp01((v - inMin) / (inMax - inMin));
    return outMin + (outMax - outMin) * t;
  };

  const makeSpring = (stiffness, damping, mass) => ({
    value: 0,
    velocity: 0,
    target: 0,
    stiffness,
    damping,
    mass,
  });

  const springX = makeSpring(55, 18, 0.9);
  const springY = makeSpring(55, 18, 0.9);
  const springProgress = makeSpring(105, 25, 1);

  const stepSpring = (s, dt) => {
    if (reduceMotion) {
      s.value = s.target;
      s.velocity = 0;
      return false;
    }
    const steps = Math.max(1, Math.ceil(dt / 0.008));
    const h = Math.min(dt, 0.064) / steps;
    for (let k = 0; k < steps; k += 1) {
      const force = -s.stiffness * (s.value - s.target) - s.damping * s.velocity;
      s.velocity += (force / s.mass) * h;
      s.value += s.velocity * h;
    }
    if (Math.abs(s.value - s.target) < 0.0006 && Math.abs(s.velocity) < 0.0006) {
      s.value = s.target;
      s.velocity = 0;
      return false;
    }
    return true;
  };

  let isOpen = false;
  let hoveredIndex = null;
  let onScreen = true;
  let pageVisible = !document.hidden;
  let pointerKind = 'mouse';
  let animFrame = 0;
  let lastTime = 0;
  let openStartTime = 0;

  const syncParticlesPause = () => {
    const paused = isOpen || !onScreen || !pageVisible || reduceMotion;
    particleSvgs.forEach((svg) => {
      if (typeof svg.pauseAnimations !== 'function') return;
      if (paused) svg.pauseAnimations();
      else svg.unpauseAnimations();
    });
  };

  const syncReducedMotionBeads = () => {
    particleSvgs.forEach((svg) => {
      svg.querySelectorAll('[data-bead-static]').forEach((g) => {
        const anim = g.querySelector('animateMotion');
        if (reduceMotion) {
          g.setAttribute('transform', g.getAttribute('data-bead-static') || '');
          if (anim) anim.remove();
        }
      });
    });
    syncParticlesPause();
  };

  syncReducedMotionBeads();
  reducedQuery.addEventListener('change', (e) => {
    reduceMotion = e.matches;
    syncReducedMotionBeads();
    applyHeroScrollParallax();
    scheduleTick();
  });

  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(
      ([entry]) => {
        onScreen = entry.isIntersecting;
        syncParticlesPause();
        if (onScreen && isOpen) scheduleTick();
      },
      { rootMargin: '40px' }
    );
    io.observe(visual);
  }

  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    syncParticlesPause();
    if (pageVisible && isOpen) {
      lastTime = 0;
      scheduleTick();
    }
  });

  const syncHoverHighlights = () => {
    stageCards.forEach((card, i) => {
      if (!card) return;
      card.classList.toggle('n3-stage-card-lit', hoveredIndex === i);
    });
    connectors.forEach((c, i) => {
      const lit = hoveredIndex === i;
      const main = i === AI_PLATE;
      if (c.lit) c.lit.setAttribute('opacity', lit ? '0.92' : '0');
      if (c.halo) c.halo.setAttribute('opacity', lit || main ? '0.26' : '0.14');
    });
  };

  const renderFrame = (nowSeconds) => {
    const x = springX.value;
    const y = springY.value;
    const p = clamp01(springProgress.value);

    parallaxLayers.forEach(({ el, reach }) => {
      el.style.transform = `translate3d(${(x * reach).toFixed(2)}px, ${(y * reach).toFixed(2)}px, 0)`;
    });

    const orbitOpacity = mapRange(p, 0, 0.6, 1, ORBIT_OPEN_OPACITY);
    orbitGroups.forEach((el) => {
      el.style.opacity = orbitOpacity.toFixed(3);
    });
    if (shadowLayer) {
      shadowLayer.style.opacity = mapRange(p, 0, 1, 1, 0.55).toFixed(3);
    }

    const rotY = x * TILT_DEGREES;
    const rotX = y * -TILT_DEGREES + p * 4;
    tiltedLayers.forEach((el) => {
      el.style.transform = `rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg)`;
    });

    const restOp = mapRange(p, 0, 0.04, 1, 0);
    const expOp = mapRange(p, 0, 0.03, 0, 1);
    if (restCore) restCore.style.opacity = restOp.toFixed(3);
    if (explodedCore) explodedCore.style.opacity = expOp.toFixed(3);
    if (hint) hint.style.opacity = mapRange(p, 0, 0.25, 1, 0).toFixed(3);

    for (let i = 0; i < 5; i += 1) {
      const delay = Math.abs(i - AI_PLATE) * STAGGER;
      const apart = clamp01((p - delay) / (1 - delay));
      const py = TRAVEL[i] * apart;
      const sc = 1 + (SCALES[i] - 1) * apart;
      const pl = plates[i];
      if (pl.g) {
        pl.g.setAttribute(
          'transform',
          `translate(0 ${py.toFixed(2)}) translate(500 ${pl.cy}) scale(${sc.toFixed(4)}) translate(-500 ${-pl.cy})`
        );
      }
      if (pl.shadow) pl.shadow.setAttribute('opacity', (apart * 0.16).toFixed(3));
      if (pl.skirt) pl.skirt.setAttribute('opacity', apart.toFixed(3));
    }

    if (strongGlow) {
      strongGlow.setAttribute('opacity', (clamp01((p - 0.4) / 0.5) * 0.55).toFixed(3));
    }
    const aiOn = clamp01((p - 0.5) / 0.4);
    const rim = aiOn * 0.88;
    const halo = aiOn * 0.55;
    if (aiSpill) aiSpill.setAttribute('opacity', (halo * 0.32).toFixed(3));
    if (aiRim) aiRim.setAttribute('opacity', rim.toFixed(3));
    if (aiHalo) aiHalo.setAttribute('opacity', halo.toFixed(3));
    if (aiCore) aiCore.setAttribute('opacity', rim.toFixed(3));

    const cardOp = mapRange(p, 0.35, 0.9, 0, 1);
    for (let i = 0; i < 5; i += 1) {
      const card = stageCards[i];
      if (!card) continue;
      const dir = SIDES[i] === 'left' ? -1 : 1;
      const tx = mapRange(p, 0, 1, -dir * REST_INSET, dir * OUTWARD);
      card.style.opacity = cardOp.toFixed(3);
      card.style.transform = `translate3d(${tx.toFixed(2)}px, 0, 0)`;
    }

    const connShow = mapRange(p, 0.55, 0.9, 0, 1);
    if (connectorsWrap) {
      connectorsWrap.style.opacity = connShow.toFixed(3);
    }

    const beadsRunning = isOpen && !reduceMotion && onScreen && pageVisible && connShow > 0.01;
    const cycle = BEAD_SECONDS + BEAD_REPEAT_DELAY;
    for (let i = 0; i < 5; i += 1) {
      const c = connectors[i];
      if (!c.bead) continue;
      if (!beadsRunning) {
        c.bead.setAttribute('opacity', '0');
        continue;
      }
      const elapsed = nowSeconds - openStartTime - (0.5 + i * 0.25);
      if (elapsed < 0) {
        c.bead.setAttribute('opacity', '0');
        continue;
      }
      const inCycle = elapsed % cycle;
      if (inCycle > BEAD_SECONDS) {
        c.bead.setAttribute('opacity', '0');
        continue;
      }
      const lin = inCycle / BEAD_SECONDS;
      const k = 0.5 - 0.5 * Math.cos(Math.PI * lin);
      const bx = c.nodeX + (c.plateX - c.nodeX) * k;
      const bOp = connShow * Math.sin(Math.PI * k);
      c.bead.setAttribute('cx', bx.toFixed(2));
      c.bead.setAttribute('opacity', bOp.toFixed(3));
    }
  };

  const tick = (ts) => {
    animFrame = 0;
    const nowSec = ts * 0.001;
    const dt = lastTime ? Math.min(0.05, (ts - lastTime) * 0.001) : 1 / 60;
    lastTime = ts;

    const mx = stepSpring(springX, dt);
    const my = stepSpring(springY, dt);
    const mp = stepSpring(springProgress, dt);

    renderFrame(nowSec);

    const keepRunningForBeads = isOpen && !reduceMotion && onScreen && pageVisible;
    if (mx || my || mp || keepRunningForBeads) {
      animFrame = requestAnimationFrame(tick);
    } else {
      lastTime = 0;
    }
  };

  function scheduleTick() {
    if (!animFrame) {
      animFrame = requestAnimationFrame(tick);
    }
  }

  const setOpen = (next) => {
    if (isOpen === next) return;
    isOpen = next;
    springProgress.target = isOpen ? 1 : 0;
    if (isOpen) {
      openStartTime = performance.now() * 0.001;
    }
    if (coreTrigger) {
      coreTrigger.setAttribute('aria-expanded', String(isOpen));
    }
    if (stageCardsList) {
      stageCardsList.setAttribute('aria-hidden', String(!isOpen));
    }
    stageCards.forEach((card) => {
      if (card) card.classList.toggle('n3-stage-card-open', isOpen);
    });
    syncParticlesPause();
    scheduleTick();
  };

  visual.addEventListener('pointermove', (e) => {
    if (reduceMotion || e.pointerType !== 'mouse') return;
    const box = visual.getBoundingClientRect();
    if (!box.width || !box.height) return;
    springX.target = ((e.clientX - box.left) / box.width - 0.5) * 2;
    springY.target = ((e.clientY - box.top) / box.height - 0.5) * 2;
    scheduleTick();
  });

  visual.addEventListener('pointerleave', () => {
    springX.target = 0;
    springY.target = 0;
    hoveredIndex = null;
    syncHoverHighlights();
    setOpen(false);
    scheduleTick();
  });

  if (coreTrigger) {
    coreTrigger.addEventListener('pointerdown', (e) => {
      pointerKind = e.pointerType;
    });

    coreTrigger.addEventListener('pointerenter', (e) => {
      if (e.pointerType === 'mouse' && !reduceMotion) {
        setOpen(true);
      }
    });

    coreTrigger.addEventListener('click', (e) => {
      if (e.detail === 0 || pointerKind !== 'mouse' || reduceMotion) {
        setOpen(!isOpen);
      }
    });

    coreTrigger.addEventListener('blur', () => {
      setOpen(false);
    });
  }

  stageCards.forEach((card, i) => {
    if (!card) return;
    card.addEventListener('pointerenter', (e) => {
      if (e.pointerType === 'mouse') {
        hoveredIndex = i;
        syncHoverHighlights();
        if (!reduceMotion) setOpen(true);
      }
    });
    card.addEventListener('pointerleave', () => {
      if (hoveredIndex === i) {
        hoveredIndex = null;
        syncHoverHighlights();
      }
    });
  });

  renderFrame(0);
})();
