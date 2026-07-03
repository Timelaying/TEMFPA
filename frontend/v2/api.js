/**
 * TEMFPA V.2 API client
 */

const API_BASE = window.TEMFPA_API_URL || 'http://localhost:8001';

/**
 * POST /api/v2/predict
 * @param {Object} requestBody - PredictionRequest payload
 * @returns {Promise<Object>} PredictionResponse or { error, code, details }
 */
export async function fetchPrediction(requestBody) {
  try {
    const response = await fetch(`${API_BASE}/api/v2/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        error: data.detail || data.error || 'Request failed',
        code: String(response.status),
        details: data.details || null,
      };
    }

    return data;
  } catch (err) {
    return {
      error: err.message || 'Network error',
      code: 'NETWORK_ERROR',
      details: 'Could not reach the TEMFPA API. Is the server running?',
    };
  }
}

/**
 * GET /api/v2/leagues
 * @returns {Promise<Array>} list of league objects
 */
export async function fetchLeagues() {
  try {
    const response = await fetch(`${API_BASE}/api/v2/leagues`);
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
}

/**
 * GET /api/v2/teams/{leagueId}?season=
 * @param {string} leagueId
 * @param {string} [season]
 * @returns {Promise<Array>} list of team objects
 */
export async function fetchTeams(leagueId, season) {
  try {
    const url = new URL(`${API_BASE}/api/v2/teams/${encodeURIComponent(leagueId)}`);
    if (season) url.searchParams.set('season', season);
    const response = await fetch(url.toString());
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
}

/**
 * GET /api/v2/fixtures?leagueId=&season=
 * @param {string} leagueId
 * @param {string} [season]
 * @returns {Promise<Array>} list of fixture objects
 */
export async function fetchFixtures(leagueId, season) {
  try {
    const url = new URL(`${API_BASE}/api/v2/fixtures`);
    if (leagueId) url.searchParams.set('leagueId', leagueId);
    if (season) url.searchParams.set('season', season);
    const response = await fetch(url.toString());
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
}
