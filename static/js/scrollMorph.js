/* ==========================================================================
   IronPulse — Scroll-Morph Stage + UI interactions
   Vanilla JS, no dependencies. Performance-first: IntersectionObserver + rAF.
   ========================================================================== */
(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));

  function toast(message, isError) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("error", Boolean(isError));
    el.classList.add("show");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => el.classList.remove("show"), 2800);
  }

  /* ---------------------- 1. Scroll-driven image morph -------------------- */
  const PHASES = [
    { phase: "PHASE 01 · STRENGTH", metric: '82.5 <small>KG BAR</small>', sub: "Progressive overload · Week 07" },
    { phase: "PHASE 02 · CARDIO", metric: '26:40 <small>5K TIME</small>', sub: "HIIT intervals · Zone 2 base" },
    { phase: "PHASE 03 · TRANSFORM", metric: '−7.6 <small>KG LOST</small>', sub: "Week 01 → Week 12 · verified" },
  ];

  const steps = $$(".story-step");
  const stageImages = $$(".stage-img");
  const railDots = $$(".rail-dots i");
  const phaseEl = $("#stagePhase");
  const metricEl = $("#stageMetric");
  const subEl = $("#stageSub");
  const railFill = $("#railFill");
  const frame = $("#stageFrame");
  const studio = $("#morphGrid");

  function setStage(index) {
    steps.forEach((el) => el.classList.toggle("is-active", Number(el.dataset.stage) === index));
    stageImages.forEach((el) => el.classList.toggle("is-active", Number(el.dataset.stage) === index));
    railDots.forEach((el) => el.classList.toggle("is-active", Number(el.dataset.stage) === index));
    const data = PHASES[index] || PHASES[0];
    if (phaseEl) phaseEl.textContent = data.phase;
    if (metricEl) metricEl.innerHTML = data.metric;
    if (subEl) subEl.textContent = data.sub;
  }

  if (steps.length && "IntersectionObserver" in window) {
    const stepObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setStage(Number(visible.target.dataset.stage));
      },
      { rootMargin: "-38% 0px -48% 0px", threshold: [0, 0.2, 0.6, 1] }
    );
    steps.forEach((step) => stepObserver.observe(step));
  }

  // Smooth scroll-linked scale + rail fill (rAF-throttled, no layout thrash).
  let morphTick = false;
  function updateMorphProgress() {
    morphTick = false;
    if (!studio || !frame) return;
    const rect = studio.getBoundingClientRect();
    const travel = Math.max(rect.height - window.innerHeight, 1);
    const progress = clamp(-rect.top / travel, 0, 1);
    if (railFill) railFill.style.width = (progress * 100).toFixed(1) + "%";
    frame.style.setProperty("--stage-scale", (1 - progress * 0.035).toFixed(4));
  }
  function onMorphScroll() {
    if (morphTick) return;
    morphTick = true;
    requestAnimationFrame(updateMorphProgress);
  }
  window.addEventListener("scroll", onMorphScroll, { passive: true });
  window.addEventListener("resize", onMorphScroll, { passive: true });
  onMorphScroll();

  /* --------------------------- 2. Reveal + counters ----------------------- */
  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12 }
    );
    $$(".reveal").forEach((el) => revealObserver.observe(el));

    const counterObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseFloat(el.dataset.target || "0");
          const decimals = String(target).includes(".") ? 1 : 0;
          const start = performance.now();
          const duration = 1100;
          function tick(now) {
            const t = clamp((now - start) / duration, 0, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            el.textContent = (target * eased).toFixed(decimals);
            if (t < 1) requestAnimationFrame(tick);
          }
          requestAnimationFrame(tick);
          observer.unobserve(el);
        });
      },
      { threshold: 0.6 }
    );
    $$(".count-up").forEach((el) => counterObserver.observe(el));
  } else {
    $$(".reveal").forEach((el) => el.classList.add("visible"));
  }

  /* ----------------------- 3. Before / after slider ---------------------- */
  const baSlider = $("#baSlider");
  const baRange = $("#baRange");
  if (baSlider && baRange) {
    function setCompare(value) {
      const pos = clamp(value, 0, 100);
      baRange.value = pos;
      baSlider.style.setProperty("--pos", pos + "%");
    }
    baRange.addEventListener("input", () => setCompare(Number(baRange.value)));
    let dragging = false;
    function dragTo(clientX) {
      const rect = baSlider.getBoundingClientRect();
      setCompare(((clientX - rect.left) / rect.width) * 100);
    }
    baSlider.addEventListener("pointerdown", (e) => {
      dragging = true;
      baSlider.setPointerCapture(e.pointerId);
      dragTo(e.clientX);
    });
    baSlider.addEventListener("pointermove", (e) => { if (dragging) dragTo(e.clientX); });
    baSlider.addEventListener("pointerup", () => { dragging = false; });
    baSlider.addEventListener("pointercancel", () => { dragging = false; });
    setCompare(50);
  }

  /* -------------------------- 4. Forms & APIs ---------------------------- */
  async function postJSON(url, payload, method) {
    const res = await fetch(url, {
      method: method || "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return res.json();
  }
  function refreshSoon(message) {
    toast(message);
    setTimeout(() => window.location.reload(), 650);
  }

  const workoutForm = $("#workoutForm");
  if (workoutForm) {
    workoutForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(workoutForm).entries());
      try {
        const result = await postJSON("/api/workouts", data);
        result.ok ? refreshSoon("Workout logged. Keep going!") : toast(result.error, true);
      } catch (_) { toast("Could not reach the server", true); }
    });
  }

  const goalForm = $("#goalForm");
  if (goalForm) {
    goalForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(goalForm).entries());
      try {
        const result = await postJSON("/api/goals", data);
        result.ok ? refreshSoon("Goal locked in.") : toast(result.error, true);
      } catch (_) { toast("Could not reach the server", true); }
    });
  }

  const photoForm = $("#photoForm");
  if (photoForm) {
    photoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch("/api/photos", { method: "POST", body: new FormData(photoForm) });
        const result = await res.json();
        result.ok ? refreshSoon("Progress photo added.") : toast(result.error, true);
      } catch (_) { toast("Could not reach the server", true); }
    });
  }

  $$("[data-goal-update]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const current = form.elements.current.value;
      try {
        const result = await postJSON(`/api/goals/${form.dataset.goalUpdate}/progress`, { current });
        result.ok ? refreshSoon("Progress updated.") : toast(result.error, true);
      } catch (_) { toast("Could not reach the server", true); }
    });
  });

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    let url = null;
    if (btn.dataset.deleteWorkout) url = `/api/workouts/${btn.dataset.deleteWorkout}`;
    else if (btn.dataset.deleteGoal) url = `/api/goals/${btn.dataset.deleteGoal}`;
    else if (btn.dataset.deletePhoto) url = `/api/photos/${btn.dataset.deletePhoto}`;
    if (!url) return;
    try {
      const res = await fetch(url, { method: "DELETE" });
      const result = await res.json();
      result.ok ? refreshSoon("Removed.") : toast("Delete failed", true);
    } catch (_) { toast("Could not reach the server", true); }
  });

  /* ---------------------- 5. BMI / BMR / TDEE calculator ----------------- */
  const calcForm = $("#calcForm");
  if (calcForm) {
    calcForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const weight = parseFloat($("#calcWeight").value) || 0;
      const heightCm = parseFloat($("#calcHeight").value) || 0;
      const age = parseFloat($("#calcAge").value) || 0;
      const sex = $("#calcSex").value;
      const activity = parseFloat($("#calcActivity").value) || 1.2;
      const meters = heightCm / 100;
      const bmi = weight / Math.max(meters * meters, 0.01);
      const bmr = 10 * weight + 6.25 * heightCm - 5 * age + (sex === "male" ? 5 : -161);
      const tdee = bmr * activity;

      const label = bmi < 18.5 ? "Underweight" : bmi < 25 ? "Normal range" : bmi < 30 ? "Overweight" : "Obese range";
      $("#bmiValue").textContent = bmi.toFixed(1);
      $("#bmiLabel").textContent = label;
      $("#bmrValue").textContent = Math.round(bmr).toLocaleString("en-IN");
      $("#tdeeValue").textContent = Math.round(tdee).toLocaleString("en-IN");
      $("#cutValue").textContent = Math.round(tdee * 0.85).toLocaleString("en-IN");
      $("#gainValue").textContent = Math.round(tdee * 1.08).toLocaleString("en-IN");
      toast("Metrics updated locally.");
    });
  }
})();
