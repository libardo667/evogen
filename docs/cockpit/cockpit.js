(function () {
  "use strict";

  const state = window.EVOGEN_COCKPIT_STATE;
  if (!state) {
    document.body.innerHTML = "<main class='noscript-card'><h1>Cockpit state is unavailable</h1><p>Run the cockpit builder and reload this checked-in page.</p></main>";
    return;
  }

  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const proofById = new Map(state.proof_lanes.map((lane) => [lane.id, lane]));

  byId("snapshot-label").textContent = state.snapshot_label;
  byId("product-thesis").textContent = state.product_thesis;
  byId("progress-complete").textContent = state.progress.completed_goal_count;
  byId("progress-total").textContent = state.progress.goal_count;
  byId("progress-fill").style.width = `${state.progress.completed_goal_count / state.progress.goal_count * 100}%`;
  byId("state-id").textContent = state.state_id.slice(0, 24) + "…";

  byId("last-closed-card").innerHTML = `
    <div class="handoff-label"><span>Last closed</span><span class="goal-id">${escapeHtml(state.last_closed_goal.goal_id)}</span></div>
    <h2>${escapeHtml(state.last_closed_goal.title)}</h2>
    <p>${escapeHtml(state.last_closed_goal.summary)}</p>`;
  byId("next-card").innerHTML = `
    <div class="handoff-label"><span>Next authorized · unstarted</span><span class="goal-id">${escapeHtml(state.current_focus.goal_id)}</span></div>
    <h2>${escapeHtml(state.current_focus.title)}</h2>
    <p>${escapeHtml(state.current_focus.summary)}</p>`;

  byId("proof-roadmap").innerHTML = state.execution_route.map((milestone, index) => `
    <article class="proof-milestone ${escapeHtml(milestone.status)}">
      <div class="milestone-top"><span class="milestone-index">${String(index + 1).padStart(2, "0")}</span><span class="capability-status status-${escapeHtml(milestone.status)}">${escapeHtml(milestone.status)}</span></div>
      <p class="milestone-goals">${escapeHtml(milestone.goals.join(" → "))}</p>
      <h3>${escapeHtml(milestone.label)}</h3>
      <p>${escapeHtml(milestone.delivers)}</p>
      <p class="milestone-boundary"><strong>Boundary:</strong> ${escapeHtml(milestone.boundary)}</p>
    </article>`).join("");

  const trajectoryProof = state.trajectory_export_proof;
  byId("trajectory-panel").innerHTML = `
    <div class="trajectory-head">
      <div><h3>${escapeHtml(trajectoryProof.title)}</h3><p>${escapeHtml(trajectoryProof.scope)}</p></div>
      <code>bundle ${escapeHtml(trajectoryProof.bundle_id.slice(0, 12))}…</code>
    </div>
    <div class="trajectory-stats">
      <div><strong>${escapeHtml(trajectoryProof.portable_source.raw_records)}</strong><span>portable raw records</span></div>
      <div><strong>${escapeHtml(trajectoryProof.portable_source.normalized_events)}</strong><span>strict events</span></div>
      <div><strong>${escapeHtml(trajectoryProof.real_run_acceptance.raw_records.toLocaleString())}</strong><span>real-run raw records checked</span></div>
      <div><strong>${escapeHtml(trajectoryProof.real_run_acceptance.normalized_events.toLocaleString())}</strong><span>real-run events parsed</span></div>
    </div>
    <div class="mapping-list">${trajectoryProof.mapping.map((item) => `
      <div class="mapping-row"><code>${escapeHtml(item.source)}</code><span aria-hidden="true">→</span><strong>${escapeHtml(item.normalized)}</strong></div>`).join("")}</div>
    <div class="trajectory-foot">
      <p><strong>Ordering:</strong> source ${escapeHtml(trajectoryProof.portable_source.source_sequence)} becomes normalized ${escapeHtml(trajectoryProof.portable_source.normalized_sequence)} in encounter order.</p>
      <p><strong>Explicitly withheld:</strong> ${escapeHtml(trajectoryProof.withheld.join(", "))}.</p>
      <p class="trajectory-boundary"><strong>Boundary:</strong> ${escapeHtml(trajectoryProof.boundary)}</p>
    </div>`;

  byId("demo-panel").innerHTML = `
    <div class="demo-head"><div><h3>${escapeHtml(state.demo_result.label)}</h3><p>${escapeHtml(state.demo_result.scope)}</p></div><span class="verdict">verdict · ${escapeHtml(state.demo_result.verdict)}</span></div>
    <div class="suite-grid">${state.demo_result.suites.map((suite) => `
      <div class="suite"><span>${escapeHtml(suite.label)}</span><div class="score-flow"><small>baseline</small>${escapeHtml(suite.baseline)} <small>→</small> <strong>${escapeHtml(suite.candidate)}</strong></div></div>`).join("")}</div>`;
  byId("command-list").innerHTML = state.commands.map((item) => `
    <div class="command"><div class="command-label">${escapeHtml(item.label)}<span>${escapeHtml(item.cwd)}</span></div><code>${escapeHtml(item.command)}</code></div>`).join("");
  byId("withheld-list").innerHTML = state.withheld_claims.map((claim) => `<li>${escapeHtml(claim)}</li>`).join("");

  byId("goal-journeys").innerHTML = state.journeys.map((journey) => {
    const goals = state.goals.filter((goal) => goal.journey_id === journey.id);
    return `<section class="journey" data-journey="${journey.id}">
      <div class="journey-head"><div><p class="eyebrow">Journey ${escapeHtml(journey.label)}</p><h2>G${String(journey.first_goal).padStart(2, "0")}–G${String(journey.last_goal).padStart(2, "0")}</h2></div><p>${escapeHtml(journey.summary)}</p></div>
      <div class="goal-list">${goals.map((goal) => `<article class="goal-row" data-goal-state="${goal.state}" data-goal-search="${escapeHtml((goal.id + " " + goal.title + " " + goal.repositories.join(" ")).toLowerCase())}">
        <span class="goal-number">${goal.id}</span><span class="goal-state ${goal.state}">${goal.state === "complete" ? "closed" : goal.state}</span><span class="goal-title">${escapeHtml(goal.title)}</span><span class="goal-repo">${escapeHtml(goal.repositories.join(" + "))}</span>
      </article>`).join("")}</div></section>`;
  }).join("");

  byId("capability-grid").innerHTML = state.capabilities.map((capability) => `
    <article class="capability-card ${capability.status}">
      <div class="capability-top"><span class="eyebrow">${escapeHtml(capability.id.replaceAll("_", " "))}</span><span class="capability-status status-${capability.status}">${escapeHtml(capability.status)}</span></div>
      <h2>${escapeHtml(capability.name)}</h2><p>${escapeHtml(capability.plain_language)}</p>
      <div class="proof-strip" aria-label="Proof lanes">${capability.proof.map((proof) => `<span class="proof-chip ${proof === "withheld" ? "withheld" : ""}" title="${escapeHtml(proofById.get(proof).description)}">${escapeHtml(proofById.get(proof).label)}</span>`).join("")}</div>
      <p class="not-proven"><strong>Boundary:</strong> ${escapeHtml(capability.not_proven)}</p>
      <div class="evidence-links">${capability.evidence.map((link) => `<a href="${escapeHtml(link.href)}">${escapeHtml(link.label)} ↗</a>`).join("")}</div>
    </article>`).join("");

  byId("evidence-ladder").innerHTML = state.proof_lanes.map((lane, index) => `
    <article class="lane"><span class="lane-index">${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(lane.label)}</strong><p>${escapeHtml(lane.description)}</p></article>`).join("");
  byId("authority-panel").innerHTML = `
    <p class="eyebrow">Snapshot provenance</p><h2>This screen is derived, not authoritative</h2>
    <dl><dt>Schema</dt><dd>${escapeHtml(state.schema_version)}</dd><dt>State identity</dt><dd>${escapeHtml(state.state_id)}</dd><dt>Input digest</dt><dd>sha256:${escapeHtml(state.source_authority.input_digest)}</dd><dt>Plan revision</dt><dd>${escapeHtml(state.source_authority.plan_revision_commit)}</dd></dl>`;

  byId("repo-grid").innerHTML = state.repositories.map((repo) => `
    <article class="repo-card ${repo.evidence_commit ? "" : "not-started"}">
      <div class="repo-kicker"><span>${escapeHtml(repo.id)}</span><span>${escapeHtml(repo.branch)}</span></div>
      <h2>${escapeHtml(repo.name)}</h2><p class="repo-role">${escapeHtml(repo.role)}</p><p>${escapeHtml(repo.state)}</p>
      <dl class="repo-facts"><div><dt>commit</dt><dd>${escapeHtml(repo.evidence_commit || "withheld")}</dd></div><div><dt>CI run</dt><dd>${escapeHtml(repo.hosted_run || "not available")}</dd></div><div><dt>matrix</dt><dd>${escapeHtml(repo.matrix || "not available")}</dd></div></dl>
      <a href="${escapeHtml(repo.href)}">Open evidence ↗</a>
    </article>`).join("");

  const navItems = [...document.querySelectorAll(".nav-item")];
  const mobileNav = byId("mobile-nav");
  const viewLabels = {
    now: "Now",
    goals: "49 goals",
    capabilities: "Capabilities",
    evidence: "Evidence",
    repositories: "Repositories",
  };
  mobileNav.innerHTML = navItems.map((item) => `<button type="button" data-view-target="${item.dataset.viewTarget}">${viewLabels[item.dataset.viewTarget]}</button>`).join("");
  const allNavItems = [...navItems, ...mobileNav.querySelectorAll("button")];
  function showView(name, updateHash = true) {
    const target = document.querySelector(`[data-view="${name}"]`);
    if (!target) return;
    document.querySelectorAll(".view").forEach((view) => { view.hidden = view !== target; view.classList.toggle("is-active", view === target); });
    allNavItems.forEach((item) => { const active = item.dataset.viewTarget === name; item.classList.toggle("is-active", active); if (item.classList.contains("nav-item")) active ? item.setAttribute("aria-current", "page") : item.removeAttribute("aria-current"); });
    if (updateHash) history.replaceState(null, "", `#${name}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  allNavItems.forEach((item) => item.addEventListener("click", () => {
    showView(item.dataset.viewTarget);
    if (item.closest(".mobile-nav")) {
      mobileNav.hidden = true;
      menuButton.setAttribute("aria-expanded", "false");
    }
  }));
  document.querySelector(".brand").addEventListener("click", (event) => { event.preventDefault(); showView("now"); });
  const initialView = location.hash.slice(1);
  if (["now", "goals", "capabilities", "evidence", "repositories"].includes(initialView)) showView(initialView, false);

  const menuButton = document.querySelector(".menu-button");
  menuButton.addEventListener("click", () => { const open = mobileNav.hidden; mobileNav.hidden = !open; menuButton.setAttribute("aria-expanded", String(open)); });

  let goalFilter = "all";
  const goalSearch = byId("goal-search");
  function filterGoals() {
    const query = goalSearch.value.trim().toLowerCase();
    document.querySelectorAll(".goal-row").forEach((row) => { const stateMatches = goalFilter === "all" || row.dataset.goalState === goalFilter; const searchMatches = !query || row.dataset.goalSearch.includes(query); row.classList.toggle("is-hidden", !(stateMatches && searchMatches)); });
    document.querySelectorAll(".journey").forEach((journey) => journey.classList.toggle("is-empty", !journey.querySelector(".goal-row:not(.is-hidden)")));
  }
  document.querySelectorAll("[data-goal-filter]").forEach((button) => button.addEventListener("click", () => { goalFilter = button.dataset.goalFilter; document.querySelectorAll("[data-goal-filter]").forEach((item) => item.classList.toggle("is-active", item === button)); filterGoals(); }));
  goalSearch.addEventListener("input", filterGoals);

})();
