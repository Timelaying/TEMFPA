/**
 * TEMFPA — Main application script
 * Handles: header scroll, mobile nav, reveal animations,
 *          league/team population, prediction form, result rendering.
 */

const API = window.TEMFPA_API_URL || 'http://localhost:8001';

// ─── Utilities ─────────────────────────────────────────────────────────────

/** Derive football season label from a date string (YYYY-MM-DD).
 *  Season runs Aug–Jul: 2025-09-20 → "2025/2026", 2025-03-10 → "2024/2025"
 */
function deriveSeason(dateStr) {
  const d = new Date(dateStr);
  const year = d.getFullYear();
  const month = d.getMonth() + 1; // 1-12
  return month >= 8 ? `${year}/${year + 1}` : `${year - 1}/${year}`;
}

function show(el) { if (el) { el.hidden = false; el.style.display = ''; } }
function hide(el) { if (el) { el.hidden = true; el.style.display = 'none'; } }

// ─── Header scroll + mobile nav ────────────────────────────────────────────

const siteHeader = document.getElementById('site-header');
window.addEventListener('scroll', () => {
  siteHeader?.classList.toggle('scrolled', window.scrollY > 20);
}, { passive: true });
siteHeader?.classList.toggle('scrolled', window.scrollY > 20);

const menuToggle = document.getElementById('menu-toggle');
const primaryNav = document.getElementById('primary-nav');
menuToggle?.addEventListener('click', () => {
  const open = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!open));
  menuToggle.setAttribute('aria-label', !open ? 'Close navigation' : 'Open navigation');
  primaryNav?.classList.toggle('open', !open);
  document.body.classList.toggle('menu-open', !open);
});
primaryNav?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  menuToggle?.setAttribute('aria-expanded', 'false');
  menuToggle?.setAttribute('aria-label', 'Open navigation');
  primaryNav.classList.remove('open');
  document.body.classList.remove('menu-open');
}));

// ─── Reveal on scroll ──────────────────────────────────────────────────────

if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
} else {
  document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
}

// ─── Footer year ───────────────────────────────────────────────────────────

const yearEl = document.getElementById('footer-year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// ─── API helpers ───────────────────────────────────────────────────────────

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${API}${path}`, opts);
  const json = await res.json();
  if (!res.ok) throw Object.assign(new Error(json.detail || json.error || 'Request failed'), { status: res.status, data: json });
  return json;
}

async function fetchLeagues() {
  try { return await apiFetch('/api/v2/leagues'); }
  catch { return []; }
}

async function fetchTeams(leagueCode) {
  try { return await apiFetch(`/api/v2/teams/${encodeURIComponent(leagueCode)}`); }
  catch { return []; }
}

async function fetchPrediction(payload) {
  return apiFetch('/api/v2/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

// ─── DOM refs ──────────────────────────────────────────────────────────────

const leagueSelect = document.getElementById('league-select');
const homeSelect   = document.getElementById('home-team');
const awaySelect   = document.getElementById('away-team');
const dateInput    = document.getElementById('match-date');
const predictForm  = document.getElementById('predict-form');
const predictBtn   = document.getElementById('predict-btn');

const resultsSection   = document.getElementById('results');
const loadingState     = document.getElementById('loading-state');
const errorBanner      = document.getElementById('error-banner');
const errorTitle       = document.getElementById('error-title');
const errorMessage     = document.getElementById('error-message');
const errorDismiss     = document.getElementById('error-dismiss');
const matchHeader      = document.getElementById('match-header');
const resultsGrid      = document.getElementById('results-grid');
const predictAgainWrap = document.getElementById('predict-again-wrap');
const predictAgainBtn  = document.getElementById('predict-again-btn');

// ─── Populate leagues ──────────────────────────────────────────────────────

async function initLeagues() {
  const leagues = await fetchLeagues();
  leagueSelect.innerHTML = '<option value="">Select league…</option>';
  leagues.forEach(lg => {
    const o = document.createElement('option');
    o.value = lg.code;
    o.textContent = lg.name;
    leagueSelect.appendChild(o);
  });
}

// ─── Populate teams when league changes ────────────────────────────────────

async function onLeagueChange() {
  const code = leagueSelect.value;
  homeSelect.innerHTML = '<option value="">Loading…</option>';
  awaySelect.innerHTML = '<option value="">Loading…</option>';
  homeSelect.disabled = true;
  awaySelect.disabled = true;

  if (!code) {
    homeSelect.innerHTML = '<option value="">Select league first…</option>';
    awaySelect.innerHTML = '<option value="">Select league first…</option>';
    return;
  }

  const teams = await fetchTeams(code);
  const opts = ['<option value="">Select team…</option>',
    ...teams.map(t => `<option value="${t.id}">${t.name}</option>`)
  ].join('');

  homeSelect.innerHTML = opts;
  awaySelect.innerHTML = opts;
  homeSelect.disabled = false;
  awaySelect.disabled = false;
}

leagueSelect?.addEventListener('change', onLeagueChange);

// Set default date to today
if (dateInput && !dateInput.value) {
  const today = new Date();
  dateInput.value = today.toISOString().slice(0, 10);
}

// ─── Validation ────────────────────────────────────────────────────────────

function clearErrors() {
  ['league-error', 'home-error', 'away-error', 'date-error'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
  ['league-select', 'home-team', 'away-team', 'match-date'].forEach(id => {
    document.getElementById(id)?.closest('.field-group')?.classList.remove('invalid');
  });
}

function setError(fieldId, errorId, msg) {
  const err = document.getElementById(errorId);
  if (err) err.textContent = msg;
  document.getElementById(fieldId)?.closest('.field-group')?.classList.add('invalid');
}

function validate() {
  clearErrors();
  let ok = true;
  if (!leagueSelect?.value) { setError('league-select', 'league-error', 'Please select a league.'); ok = false; }
  if (!homeSelect?.value) { setError('home-team', 'home-error', 'Please select the home team.'); ok = false; }
  if (!awaySelect?.value) { setError('away-team', 'away-error', 'Please select the away team.'); ok = false; }
  if (homeSelect?.value && awaySelect?.value && homeSelect.value === awaySelect.value) {
    setError('away-team', 'away-error', 'Home and away teams must be different.'); ok = false;
  }
  if (!dateInput?.value) { setError('match-date', 'date-error', 'Please enter a match date.'); ok = false; }
  return ok;
}

// ─── Show / hide results ───────────────────────────────────────────────────

function showLoading() {
  show(resultsSection);
  show(loadingState);
  hide(errorBanner);
  hide(matchHeader);
  hide(resultsGrid);
  hide(predictAgainWrap);
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(title, message) {
  hide(loadingState);
  hide(resultsGrid);
  hide(matchHeader);
  hide(predictAgainWrap);
  show(errorBanner);
  if (errorTitle) errorTitle.textContent = title;
  if (errorMessage) errorMessage.textContent = message;
}

function showResults() {
  hide(loadingState);
  hide(errorBanner);
  show(matchHeader);
  show(resultsGrid);
  show(predictAgainWrap);
}

errorDismiss?.addEventListener('click', () => hide(errorBanner));
predictAgainBtn?.addEventListener('click', () => {
  hide(resultsSection);
  document.getElementById('predict-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

// ─── Render helpers ────────────────────────────────────────────────────────

function setEl(id, content) {
  const el = document.getElementById(id);
  if (el) el.textContent = content;
}

function renderMatchHeader(response) {
  const { fixture } = response;
  setEl('match-league', `${fixture.league} · ${deriveSeason(fixture.date)}`);
  const leagueCode = document.getElementById('league-select')?.value || '';
  const hf = teamFlag(fixture.homeTeam?.name || '', leagueCode);
  const af = teamFlag(fixture.awayTeam?.name || '', leagueCode);
  setEl('match-home-name', `${hf} ${fixture.homeTeam?.name || ''}`);
  setEl('match-away-name', `${af} ${fixture.awayTeam?.name || ''}`);
  setEl('match-date-display', new Date(fixture.date).toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }));
}

function renderPredictionCard(response) {
  const { prediction, fixture } = response;
  const homeProb = Math.round((prediction.homeWinProbability || 0) * 100);
  const drawProb = Math.round((prediction.drawProbability || 0) * 100);
  const awayProb = Math.round((prediction.awayWinProbability || 0) * 100);

  setEl('predicted-result', prediction.result || '—');
  setEl('likely-score', prediction.likelyScore || '—');
  setEl('xg-home', (prediction.predictedHomeGoals || 0).toFixed(2));
  setEl('xg-away', (prediction.predictedAwayGoals || 0).toFixed(2));
  setEl('prob-home-label', fixture?.homeTeam?.name || 'Home');
  setEl('prob-away-label', fixture?.awayTeam?.name || 'Away');
  setEl('prob-home-pct', `${homeProb}%`);
  setEl('prob-draw-pct', `${drawProb}%`);
  setEl('prob-away-pct', `${awayProb}%`);

  const bar = document.getElementById('prob-home-bar');
  const barDraw = document.getElementById('prob-draw-bar');
  const barAway = document.getElementById('prob-away-bar');
  if (bar) bar.style.width = `${homeProb}%`;
  if (barDraw) barDraw.style.width = `${drawProb}%`;
  if (barAway) barAway.style.width = `${awayProb}%`;

  const badge = document.getElementById('confidence-badge');
  if (badge) {
    badge.textContent = `${prediction.confidence} confidence`;
    badge.className = `confidence-badge badge-${prediction.confidence}`;
  }
}

function renderScorelines(scorelines) {
  const list = document.getElementById('scorelines-list');
  if (!list) return;
  if (!scorelines?.length) { list.innerHTML = '<p style="color:var(--ink-soft);font-size:14px;">No scoreline data available.</p>'; return; }
  const labels = ['Most likely', '2nd most likely', '3rd most likely'];
  list.innerHTML = scorelines.slice(0, 3).map((s, i) => `
    <div class="scoreline-item">
      <span class="scoreline-rank">${labels[i] || `#${i + 1}`}</span>
      <span class="scoreline-score">${s.score}</span>
      <span class="scoreline-prob">${Math.round(s.probability * 100)}%</span>
    </div>
  `).join('');
}

function renderComparison(response) {
  const grid = document.getElementById('comparison-grid');
  if (!grid) return;
  const tc = response.teamComparison;
  const home = response.fixture?.homeTeam?.name || 'Home';
  const away = response.fixture?.awayTeam?.name || 'Away';

  function formBadges(formStr) {
    if (!formStr || formStr === 'N/A') return '<span style="color:var(--ink-soft);font-size:13px">No recent data</span>';
    return formStr.split('-').map(r => `<span class="form-badge form-badge-${r}">${r}</span>`).join('');
  }

  function col(teamName, form) {
    return `
      <div class="comparison-col">
        <h4>${teamName}</h4>
        <div class="comparison-stat"><span>Form (last 5)</span><div class="form-badges">${formBadges(form.formLast5)}</div></div>
        <div class="comparison-stat"><span>Goals/game</span><strong>${form.goalsPerGame?.toFixed(2) ?? '—'}</strong></div>
        <div class="comparison-stat"><span>Conceded/game</span><strong>${form.concededPerGame?.toFixed(2) ?? '—'}</strong></div>
      </div>
    `;
  }

  grid.innerHTML = col(home, tc.homeForm) + col(away, tc.awayForm);
}

function renderFactors(keyFactors) {
  const list = document.getElementById('factors-list');
  if (!list) return;
  if (!keyFactors?.length) { list.innerHTML = '<li style="color:var(--ink-soft)">No key factors available.</li>'; return; }
  list.innerHTML = keyFactors.map(f => {
    const icon = f.impact === 'positive' ? '↑' : f.impact === 'negative' ? '↓' : '—';
    return `
      <li class="factor-item factor-item-${f.impact || 'neutral'}">
        <span class="factor-icon" aria-hidden="true">${icon}</span>
        <span>${f.description}</span>
      </li>
    `;
  }).join('');
}

function renderFormation(formationImpact) {
  const card = document.getElementById('formation-card');
  const content = document.getElementById('formation-content');
  if (!card || !content) return;

  if (!formationImpact || (!formationImpact.homeFormation && !formationImpact.awayFormation)) {
    hide(card); return;
  }

  const rows = [];
  if (formationImpact.homeFormation) {
    rows.push(`<tr>
      <td>Home</td>
      <td><span class="formation-badge">${formationImpact.homeFormation}</span></td>
      <td>${formationImpact.homeFormationWinPercent != null ? `${formationImpact.homeFormationWinPercent}%` : '—'}</td>
    </tr>`);
  }
  if (formationImpact.awayFormation) {
    rows.push(`<tr>
      <td>Away</td>
      <td><span class="formation-badge">${formationImpact.awayFormation}</span></td>
      <td>${formationImpact.awayFormationWinPercent != null ? `${formationImpact.awayFormationWinPercent}%` : '—'}</td>
    </tr>`);
  }

  content.innerHTML = `
    <table class="formation-table">
      <thead><tr><th>Team</th><th>Formation</th><th>Win %</th></tr></thead>
      <tbody>${rows.join('')}</tbody>
    </table>
    ${formationImpact.formationComment ? `<p class="formation-note">${formationImpact.formationComment}</p>` : ''}
  `;
  show(card);
}

function renderPlayerImpact(playerImpact) {
  const card = document.getElementById('players-card');
  const content = document.getElementById('players-content');
  if (!card || !content) return;

  if (!playerImpact?.length) { hide(card); return; }

  const rows = playerImpact.map(p => `
    <tr>
      <td><strong>${p.playerName}</strong></td>
      <td>${p.team}</td>
      <td><span class="status-badge">${p.status}</span></td>
      <td>${p.teamWinPercentWithPlayer}%</td>
      <td>${p.teamWinPercentWithoutPlayer}%</td>
    </tr>
  `).join('');

  content.innerHTML = `
    <div class="players-table-wrap" style="overflow-x:auto">
      <table class="players-table">
        <thead><tr><th>Player</th><th>Team</th><th>Status</th><th>Win% With</th><th>Win% Without</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
  show(card);
}

// ─── Form submit ────────────────────────────────────────────────────────────

predictForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validate()) return;

  const leagueId   = leagueSelect.value;
  const homeTeamId = parseInt(homeSelect.value, 10);
  const awayTeamId = parseInt(awaySelect.value, 10);
  const fixtureDate = dateInput.value;
  const season = deriveSeason(fixtureDate);

  predictBtn.disabled = true;
  predictBtn.textContent = 'Predicting…';
  showLoading();

  let result;
  try {
    result = await fetchPrediction({
      leagueId, season, homeTeamId, awayTeamId, fixtureDate,
      includeScorePrediction: true,
      includeFormationImpact: true,
      includePlayerImpact: true,
    });
  } catch (err) {
    const msg = err?.data?.detail || err.message || 'An unexpected error occurred.';
    showError('Prediction failed', msg);
    predictBtn.disabled = false;
    predictBtn.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m10 2 1.5 5.2L17 9l-5.5 1.8L10 16l-1.5-5.2L3 9l5.5-1.8L10 2Z"/></svg> Predict Match`;
    return;
  }

  // Render each section independently — a render failure is non-fatal
  try { renderMatchHeader(result); } catch(e) { console.error('renderMatchHeader:', e); }
  try { renderPredictionCard(result); } catch(e) { console.error('renderPredictionCard:', e); }
  try { renderScorelines(result.topScorelines); } catch(e) { console.error('renderScorelines:', e); }
  try { renderComparison(result); } catch(e) { console.error('renderComparison:', e); }
  try { renderFactors(result.keyFactors); } catch(e) { console.error('renderFactors:', e); }
  try { renderFormation(result.formationImpact); } catch(e) { console.error('renderFormation:', e); }
  try { renderPlayerImpact(result.playerImpact); } catch(e) { console.error('renderPlayerImpact:', e); }
  try {
    const reasonEl = document.getElementById('confidence-reason');
    if (reasonEl) reasonEl.textContent = buildConfidenceReason(result);
  } catch(e) { console.error('confidenceReason:', e); }
  try { saveToHistory(result); } catch(e) { console.error('saveToHistory:', e); }

  showResults();
  predictBtn.disabled = false;
  predictBtn.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m10 2 1.5 5.2L17 9l-5.5 1.8L10 16l-1.5-5.2L3 9l5.5-1.8L10 2Z"/></svg> Predict Match`;
});

// ─── Prediction history (localStorage) ────────────────────────────────────

const HISTORY_KEY = 'temfpa_predictions';
const MAX_HISTORY = 8;

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function saveToHistory(result) {
  const history = loadHistory();
  const entry = {
    id: Date.now(),
    homeTeam: result.fixture.homeTeam.name,
    awayTeam: result.fixture.awayTeam.name,
    league: result.fixture.league,
    date: result.fixture.date,
    prediction: result.prediction.result,
    confidence: result.prediction.confidence,
    score: result.prediction.likelyScore,
    homeProb: result.prediction.homeWinProbability,
    drawProb: result.prediction.drawProbability,
    awayProb: result.prediction.awayWinProbability,
    savedAt: new Date().toISOString(),
  };
  history.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  renderHistory();
}

function renderHistory() {
  const section = document.getElementById('history-section');
  const list = document.getElementById('history-list');
  if (!section || !list) return;
  const history = loadHistory();
  if (!history.length) { hide(section); return; }

  show(section);
  list.innerHTML = history.map(e => {
    const hp = Math.round(e.homeProb * 100);
    const dp = Math.round(e.drawProb * 100);
    const ap = Math.round(e.awayProb * 100);
    const dateStr = new Date(e.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    return `
      <div class="history-item">
        <div class="history-match">
          <span class="history-teams">${e.homeTeam} <span class="history-vs">vs</span> ${e.awayTeam}</span>
          <span class="history-meta">${e.league} · ${dateStr}</span>
        </div>
        <div class="history-result">
          <span class="history-pred badge-${e.confidence}">${e.prediction}</span>
          <span class="history-score">${e.score}</span>
        </div>
        <div class="history-probs">
          <span>${hp}%</span><span class="prob-sep">·</span><span>${dp}%</span><span class="prob-sep">·</span><span>${ap}%</span>
        </div>
      </div>
    `;
  }).join('');
}

document.getElementById('clear-history-btn')?.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
});

// ─── Confidence reason ─────────────────────────────────────────────────────

function buildConfidenceReason(result) {
  const { prediction, keyFactors } = result;
  const homeProb = prediction.homeWinProbability;
  const awayProb = prediction.awayWinProbability;
  const maxProb = Math.max(homeProb, prediction.drawProbability, awayProb);
  const gap = Math.abs(homeProb - awayProb);

  const reasons = [];
  if (maxProb > 0.65) reasons.push('strong probability gap');
  else if (maxProb > 0.5) reasons.push('moderate probability gap');
  else reasons.push('close matchup');

  const formFactor = keyFactors?.find(f => f.factor === 'home_form' || f.factor === 'away_form');
  if (formFactor && formFactor.impact !== 'neutral') reasons.push('recent form trend');

  const h2h = keyFactors?.find(f => f.factor === 'h2h_limited');
  if (h2h) reasons.push('limited head-to-head data');

  return `${prediction.confidence} confidence — ${reasons.join(', ')}.`;
}

// ─── Proactive upcoming predictions ───────────────────────────────────────

const LEAGUE_FLAGS = {
  EPL: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', LA_LIGA: '🇪🇸', BUNDESLIGA: '🇩🇪',
  SERIE_A: '🇮🇹', LIGUE_1: '🇫🇷', UCL: '🏆', WORLD_CUP: '🌍',
};

// National team & club flags — keyed by exact team name from DB
const TEAM_FLAGS = {
  // ── World Cup national teams ──────────────────────────────────────
  'Algeria': '🇩🇿', 'Argentina': '🇦🇷', 'Australia': '🇦🇺',
  'Austria': '🇦🇹', 'Belgium': '🇧🇪', 'Bosnia-Herz': '🇧🇦',
  'Brazil': '🇧🇷', 'Cabo Verde': '🇨🇻', 'Canada': '🇨🇦',
  'Colombia': '🇨🇴', 'Congo DR': '🇨🇩', 'Croatia': '🇭🇷',
  'Curaçao': '🇨🇼', 'Czechia': '🇨🇿', "Côte d'Ivoire": '🇨🇮',
  'Ecuador': '🇪🇨', 'Egypt': '🇪🇬', 'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'France': '🇫🇷', 'Germany': '🇩🇪', 'Ghana': '🇬🇭',
  'Haiti': '🇭🇹', 'IR Iran': '🇮🇷', 'Iraq': '🇮🇶',
  'Japan': '🇯🇵', 'Jordan': '🇯🇴', 'Korea Republic': '🇰🇷',
  'Mexico': '🇲🇽', 'Morocco': '🇲🇦', 'Netherlands': '🇳🇱',
  'New Zealand': '🇳🇿', 'Norway': '🇳🇴', 'Panama': '🇵🇦',
  'Paraguay': '🇵🇾', 'Portugal': '🇵🇹', 'Qatar': '🇶🇦',
  'Saudi Arabia': '🇸🇦', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'Senegal': '🇸🇳',
  'South Africa': '🇿🇦', 'Spain': '🇪🇸', 'Sweden': '🇸🇪',
  'Switzerland': '🇨🇭', 'Tunisia': '🇹🇳', 'Türkiye': '🇹🇷',
  'United States': '🇺🇸', 'Uruguay': '🇺🇾', 'Uzbekistan': '🇺🇿',
  // ── EPL clubs ─────────────────────────────────────────────────────
  'Arsenal': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Aston Villa': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Bournemouth': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Brentford': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Brighton & Hove Albion': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Chelsea': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Crystal Palace': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Everton': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Fulham': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Ipswich Town': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Leicester City': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Liverpool': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Manchester City': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Manchester United': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Newcastle United': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Nottingham Forest': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Southampton': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Tottenham Hotspur': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'West Ham United': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Wolverhampton Wanderers': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  // ── La Liga clubs ─────────────────────────────────────────────────
  'Real Madrid': '🇪🇸', 'Barcelona': '🇪🇸', 'Atletico Madrid': '🇪🇸',
  'Athletic Bilbao': '🇪🇸', 'Real Sociedad': '🇪🇸', 'Villarreal': '🇪🇸',
  'Betis': '🇪🇸', 'Sevilla': '🇪🇸', 'Valencia': '🇪🇸',
  'Osasuna': '🇪🇸', 'Celta Vigo': '🇪🇸', 'Girona': '🇪🇸',
  'Rayo Vallecano': '🇪🇸', 'Mallorca': '🇪🇸', 'Getafe': '🇪🇸',
  'Leganes': '🇪🇸', 'Real Valladolid': '🇪🇸', 'Las Palmas': '🇪🇸',
  'Espanyol': '🇪🇸', 'Alaves': '🇪🇸',
  // ── Bundesliga clubs ──────────────────────────────────────────────
  'Bayern Munich': '🇩🇪', 'Borussia Dortmund': '🇩🇪',
  'Bayer Leverkusen': '🇩🇪', 'RB Leipzig': '🇩🇪',
  'Eintracht Frankfurt': '🇩🇪', 'Stuttgart': '🇩🇪',
  'Borussia Monchengladbach': '🇩🇪', 'Freiburg': '🇩🇪',
  'SC Freiburg': '🇩🇪', 'Hoffenheim': '🇩🇪', 'Werder Bremen': '🇩🇪',
  'Mainz': '🇩🇪', 'Augsburg': '🇩🇪', 'Union Berlin': '🇩🇪',
  'Wolfsburg': '🇩🇪', 'St. Pauli': '🇩🇪', 'Holstein Kiel': '🇩🇪',
  'Hamburger SV': '🇩🇪',
  // ── Serie A clubs ─────────────────────────────────────────────────
  'Inter Milan': '🇮🇹', 'AC Milan': '🇮🇹', 'Juventus': '🇮🇹',
  'Napoli': '🇮🇹', 'Atalanta': '🇮🇹', 'Lazio': '🇮🇹',
  'Roma': '🇮🇹', 'Fiorentina': '🇮🇹', 'Bologna': '🇮🇹',
  'Torino': '🇮🇹', 'Monza': '🇮🇹', 'Genoa': '🇮🇹',
  'Udinese': '🇮🇹', 'Cagliari': '🇮🇹', 'Lecce': '🇮🇹',
  'Empoli': '🇮🇹', 'Hellas Verona': '🇮🇹', 'Como': '🇮🇹',
  'Parma': '🇮🇹', 'Venezia': '🇮🇹',
  // ── Ligue 1 clubs ─────────────────────────────────────────────────
  'Paris Saint-Germain': '🇫🇷', 'Monaco': '🇲🇨', 'Lille': '🇫🇷',
  'Lyon': '🇫🇷', 'Nice': '🇫🇷', 'Marseille': '🇫🇷',
  'Lens': '🇫🇷', 'Rennes': '🇫🇷', 'Strasbourg': '🇫🇷',
  'Toulouse': '🇫🇷', 'Brest': '🇫🇷', 'Reims': '🇫🇷',
  'Nantes': '🇫🇷', 'Montpellier': '🇫🇷', 'Auxerre': '🇫🇷',
  'Angers': '🇫🇷', 'Saint-Etienne': '🇫🇷', 'Le Havre': '🇫🇷',
  // ── UCL non-Big5 clubs ────────────────────────────────────────────
  'Benfica': '🇵🇹', 'Porto': '🇵🇹', 'Sporting CP': '🇵🇹',
  'Sporting Lisbon': '🇵🇹', 'Braga': '🇵🇹',
  'Ajax': '🇳🇱', 'PSV Eindhoven': '🇳🇱', 'Feyenoord': '🇳🇱', 'AZ Alkmaar': '🇳🇱',
  'Celtic': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'Rangers': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'Club Brugge': '🇧🇪', 'Anderlecht': '🇧🇪', 'Antwerp': '🇧🇪',
  'Galatasaray': '🇹🇷', 'Fenerbahce': '🇹🇷', 'Besiktas': '🇹🇷',
  'Shakhtar Donetsk': '🇺🇦', 'Dynamo Kyiv': '🇺🇦',
  'Red Star Belgrade': '🇷🇸', 'GNK Dinamo Zagreb': '🇭🇷',
  'Copenhagen': '🇩🇰', 'Young Boys': '🇨🇭',
  'Red Bull Salzburg': '🇦🇹', 'Sturm Graz': '🇦🇹',
  'Slavia Prague': '🇨🇿',
};

/** Return flag emoji for a team name, falling back to the league flag. */
function teamFlag(name, leagueCode) {
  return TEAM_FLAGS[name] || LEAGUE_FLAGS[leagueCode] || '⚽';
}

async function loadUpcomingPredictions() {
  const grid = document.getElementById('upcoming-grid');
  const loading = document.getElementById('upcoming-loading');
  if (!grid || !loading) return;

  show(loading);
  hide(grid);

  try {
    const preds = await apiFetch('/api/v2/upcoming-predictions?limit=8');
    grid.innerHTML = preds.map(p => renderUpcomingCard(p)).join('');
    hide(loading);
    show(grid);

    // Wire "Predict this" buttons
    grid.querySelectorAll('.upcoming-predict-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const league = btn.dataset.league;
        const home = btn.dataset.home;
        const away = btn.dataset.away;
        const date = btn.dataset.date;
        // Pre-fill the form and scroll to it
        if (leagueSelect) {
          leagueSelect.value = league;
          leagueSelect.dispatchEvent(new Event('change'));
          setTimeout(() => {
            if (homeSelect) homeSelect.value = home;
            if (awaySelect) awaySelect.value = away;
            if (dateInput) dateInput.value = date;
          }, 600);
        }
        document.getElementById('predict-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });
  } catch (err) {
    hide(loading);
    console.error('Failed to load upcoming predictions:', err);
  }
}

function renderUpcomingCard(p) {
  const flag = LEAGUE_FLAGS[p.leagueCode] || '⚽';
  const hp = Math.round(p.homeWinProbability * 100);
  const dp = Math.round(p.drawProbability * 100);
  const ap = Math.round(p.awayWinProbability * 100);
  const winnerClass = p.resultKey === 'home' ? 'winner-home'
                    : p.resultKey === 'away' ? 'winner-away' : 'winner-draw';
  const dateStr = new Date(p.fixtureDate + 'T12:00:00').toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short'
  });

  const homeFlag = teamFlag(p.homeTeam.name, p.leagueCode);
  const awayFlag = teamFlag(p.awayTeam.name, p.leagueCode);

  return `
    <article class="upcoming-card ${winnerClass}" data-league="${p.leagueCode}">
      <div class="upcoming-card-top">
        <span class="upcoming-league">${flag} ${p.league}</span>
        <span class="upcoming-date">${dateStr}</span>
      </div>
      <div class="upcoming-teams">
        <span class="upcoming-team ${p.resultKey === 'home' ? 'predicted-winner' : ''}"><span class="team-flag">${homeFlag}</span>${p.homeTeam.name}</span>
        <div class="upcoming-score-box">
          <span class="upcoming-score">${p.likelyScore}</span>
          <span class="upcoming-confidence badge-${p.confidence}">${p.confidence}</span>
        </div>
        <span class="upcoming-team away-team ${p.resultKey === 'away' ? 'predicted-winner' : ''}"><span class="team-flag">${awayFlag}</span>${p.awayTeam.name}</span>
      </div>
      <div class="upcoming-probs">
        <div class="upcoming-bar">
          <span class="bar-home" style="width:${hp}%"></span>
          <span class="bar-draw" style="width:${dp}%"></span>
          <span class="bar-away" style="width:${ap}%"></span>
        </div>
        <div class="upcoming-prob-labels">
          <span>${hp}% W</span><span>${dp}% D</span><span>${ap}% W</span>
        </div>
      </div>
      <button class="upcoming-predict-btn"
        data-league="${p.leagueCode}"
        data-home="${p.homeTeam.id}"
        data-away="${p.awayTeam.id}"
        data-date="${p.fixtureDate}">
        Full prediction →
      </button>
    </article>
  `;
}

document.getElementById('refresh-upcoming-btn')?.addEventListener('click', loadUpcomingPredictions);

// ─── Prediction accuracy panel ─────────────────────────────────────────────

let _accTrendChart = null;
let _accActiveLeague = null;
let _accData = null;

function _renderRecentList(recent) {
  const recentList = document.getElementById('acc-recent-list');
  if (!recentList || !recent) return;
  if (!recent.length) {
    recentList.innerHTML = '<p style="color:var(--ink-soft);font-size:13px;padding:12px 0">No predictions yet for this filter.</p>';
    return;
  }
  recentList.innerHTML = recent.map(r => {
    let icon, iconClass;
    if (r.is_correct === null || r.is_correct === undefined) {
      icon = '·'; iconClass = 'acc-result-pending';
    } else if (r.is_correct) {
      icon = '✓'; iconClass = 'acc-result-correct';
    } else {
      icon = '✗'; iconClass = 'acc-result-wrong';
    }
    const dateStr = new Date(r.fixture_date + 'T12:00:00').toLocaleDateString('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
    const flag = LEAGUE_FLAGS[r.league_code] || '⚽';
    const resultLabel = r.predicted_result === 'home' ? r.home_team
                      : r.predicted_result === 'away' ? r.away_team : 'Draw';
    const actualScore = (r.actual_home_goals != null && r.actual_away_goals != null)
      ? `${r.actual_home_goals}–${r.actual_away_goals}` : '';
    const predictedScore = r.likely_score ? r.likely_score.replace('-', '–') : '';
    const scoreCompare = actualScore
      ? `<span class="acc-score-compare"><span class="acc-score-pred" title="Predicted">${predictedScore}</span><span class="acc-score-sep">→</span><span class="acc-score-actual">${actualScore}</span></span>`
      : (predictedScore ? `<span class="acc-score-compare"><span class="acc-score-pred">${predictedScore}</span></span>` : '<span></span>');

    const hFlag = teamFlag(r.home_team, r.league_code);
    const aFlag = teamFlag(r.away_team, r.league_code);
    return `<div class="acc-recent-item">
      <div>
        <div class="acc-recent-teams"><span class="team-flag">${hFlag}</span>${r.home_team} <span class="acc-vs">vs</span> <span class="team-flag">${aFlag}</span>${r.away_team}</div>
        <div class="acc-recent-meta">${flag} ${r.league_code} · ${dateStr}</div>
      </div>
      <span class="acc-recent-pred badge-${r.predicted_confidence}">${resultLabel}</span>
      ${scoreCompare}
      <span class="acc-result-icon ${iconClass}" title="${r.is_correct == null ? 'Pending' : r.is_correct ? 'Correct' : 'Incorrect'}">${icon}</span>
    </div>`;
  }).join('');
}

function _renderTrendChart(trend) {
  const block = document.getElementById('acc-chart-block');
  const canvas = document.getElementById('acc-trend-chart');
  if (!block || !canvas || !trend || trend.length < 3) return;

  show(block);

  const labels = trend.map(t => `#${t.n}`);
  const values = trend.map(t => t.cumulative_accuracy);

  if (_accTrendChart) {
    _accTrendChart.data.labels = labels;
    _accTrendChart.data.datasets[0].data = values;
    _accTrendChart.update();
    return;
  }

  _accTrendChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Cumulative accuracy %',
        data: values,
        borderColor: '#0b7a4d',
        backgroundColor: 'rgba(11,122,77,0.08)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#0b7a4d',
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y}% accuracy after ${ctx.label}`,
          },
        },
      },
      scales: {
        y: {
          min: 0, max: 100,
          ticks: { callback: v => `${v}%` },
          grid: { color: 'rgba(7,18,14,.06)' },
        },
        x: { grid: { display: false } },
      },
    },
  });
}

function _buildLeagueFilters(byLeague, allRecent) {
  const container = document.getElementById('acc-league-filters');
  if (!container || !byLeague) return;

  const codes = Object.keys(byLeague).sort();
  if (codes.length < 2) { container.innerHTML = ''; return; }

  const allBtn = `<button class="acc-filter-btn active" data-league="">All</button>`;
  const leagueBtns = codes.map(code => {
    const flag = LEAGUE_FLAGS[code] || '⚽';
    return `<button class="acc-filter-btn" data-league="${code}">${flag} ${code}</button>`;
  }).join('');
  container.innerHTML = allBtn + leagueBtns;

  container.querySelectorAll('.acc-filter-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      container.querySelectorAll('.acc-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const league = btn.dataset.league;
      _accActiveLeague = league || null;

      // Fetch filtered recent list from API
      try {
        const url = league ? `/api/v2/predictions/accuracy?league=${league}` : '/api/v2/predictions/accuracy';
        const filtered = await apiFetch(url);
        _renderRecentList(filtered.recent);
      } catch (e) {
        console.error('Filter fetch failed:', e);
      }
    });
  });
}

async function loadAccuracyStats() {
  const section = document.getElementById('accuracy-section');
  if (!section) return;

  let data;
  try {
    data = await apiFetch('/api/v2/predictions/accuracy');
  } catch (err) {
    console.error('Failed to load accuracy stats:', err);
    return;
  }
  _accData = data;

  const { overall, by_confidence, by_league, trend, recent } = data;

  // Show section only once there is at least one resolved prediction
  if (!overall || overall.total === 0) {
    // Still show the section so the sync button is accessible
    show(section);
  }

  const setEl = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  setEl('acc-total', overall.total || '—');
  setEl('acc-correct', overall.correct || '—');
  setEl('acc-pct', overall.total ? `${overall.accuracy_pct}%` : '—');
  setEl('acc-brier', overall.brier_score != null ? overall.brier_score : '—');

  // Trend chart
  if (trend && trend.length >= 3) _renderTrendChart(trend);

  // By confidence
  const confRows = document.getElementById('acc-confidence-rows');
  if (confRows && by_confidence && Object.keys(by_confidence).length) {
    confRows.innerHTML = ['High', 'Medium', 'Low']
      .filter(k => by_confidence[k])
      .map(k => {
        const d = by_confidence[k];
        return `<div class="accuracy-row">
          <span class="accuracy-row-label">${k}</span>
          <span class="accuracy-row-stat">${d.correct}/${d.total}</span>
          <span class="accuracy-row-pct">${d.accuracy_pct}%</span>
        </div>`;
      }).join('');
  } else if (confRows) {
    confRows.innerHTML = '<p style="color:var(--ink-soft);font-size:13px;padding:8px 0">No resolved predictions yet.</p>';
  }

  // By league
  const leagueRows = document.getElementById('acc-league-rows');
  if (leagueRows && by_league && Object.keys(by_league).length) {
    leagueRows.innerHTML = Object.entries(by_league)
      .sort((a, b) => b[1].total - a[1].total)
      .map(([code, d]) => {
        const flag = LEAGUE_FLAGS[code] || '⚽';
        return `<div class="accuracy-row">
          <span class="accuracy-row-label">${flag} ${code}</span>
          <span class="accuracy-row-stat">${d.correct}/${d.total}</span>
          <span class="accuracy-row-pct">${d.accuracy_pct}%</span>
        </div>`;
      }).join('');
  }

  // League filter buttons
  _buildLeagueFilters(by_league, recent);

  // Recent list
  _renderRecentList(recent);

  show(section);
}

// ─── Sync trigger ──────────────────────────────────────────────────────────

document.getElementById('sync-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('sync-btn');
  const status = document.getElementById('sync-status');
  if (!btn || !status) return;

  // Fetch available leagues from the API
  let leagues;
  try {
    leagues = await apiFetch('/api/v2/sync/leagues');
  } catch {
    leagues = [{ league: 'WORLD_CUP', season: '2026' }];
  }

  btn.disabled = true;
  btn.textContent = 'Syncing…';
  status.className = 'sync-status syncing';
  status.textContent = `Syncing ${leagues.length} league(s) in background — this may take a minute…`;
  show(status);

  let successCount = 0;
  let errorCount = 0;

  for (const lg of leagues) {
    try {
      await fetch(`${API}/api/v2/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          league: lg.league,
          season: lg.season,
          skip_lineups: true,
          skip_player_stats: true,
        }),
      });
      successCount++;
    } catch {
      errorCount++;
    }
  }

  btn.disabled = false;
  btn.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true" style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:4px"><path d="M4 10a6 6 0 1 1 1.5 4"/><path d="M4 14v-4H8"/></svg>Sync results`;

  if (errorCount === 0) {
    status.className = 'sync-status done';
    status.textContent = `✓ Sync queued for ${successCount} league(s). Reload the page in ~2 minutes to see updated accuracy.`;
  } else {
    status.className = 'sync-status error';
    status.textContent = `Sync queued with ${errorCount} error(s). Check server logs.`;
  }

  // Reload accuracy stats after a short delay
  setTimeout(loadAccuracyStats, 3000);
});

// ─── Boot ──────────────────────────────────────────────────────────────────

initLeagues();
renderHistory();
loadUpcomingPredictions();
loadAccuracyStats();
