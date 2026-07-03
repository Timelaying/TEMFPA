/**
 * Renders the main prediction card with result, confidence badge, and probability bar.
 */
export function renderPredictionCard(response, container) {
  if (!response || !response.prediction) {
    container.innerHTML = '<p class="v2-empty">No prediction data available.</p>';
    return;
  }

  const pred = response.prediction;
  const homeProb = Math.round(pred.homeWinProbability * 100);
  const drawProb = Math.round(pred.drawProbability * 100);
  const awayProb = Math.round(pred.awayWinProbability * 100);

  const homeTeam = response.fixture?.homeTeam?.name || 'Home';
  const awayTeam = response.fixture?.awayTeam?.name || 'Away';

  const confidenceClass = {
    High: 'badge-high',
    Medium: 'badge-medium',
    Low: 'badge-low',
  }[pred.confidence] || 'badge-medium';

  container.innerHTML = `
    <article class="v2-prediction-card">
      <div class="v2-prediction-header">
        <div class="v2-prediction-result">
          <span class="v2-result-label">${pred.result}</span>
          <span class="v2-confidence-badge ${confidenceClass}">${pred.confidence} Confidence</span>
        </div>
        <div class="v2-score-info">
          <span class="v2-score-label">Most likely score</span>
          <strong class="v2-score-value">${pred.likelyScore}</strong>
        </div>
      </div>

      <div class="v2-probability-bar" aria-label="Win probabilities: ${homeTeam} ${homeProb}%, Draw ${drawProb}%, ${awayTeam} ${awayProb}%">
        <span class="v2-prob-home" style="width:${homeProb}%" title="${homeTeam}: ${homeProb}%"></span>
        <span class="v2-prob-draw" style="width:${drawProb}%" title="Draw: ${drawProb}%"></span>
        <span class="v2-prob-away" style="width:${awayProb}%" title="${awayTeam}: ${awayProb}%"></span>
      </div>

      <div class="v2-probability-labels">
        <span>
          <i class="v2-dot v2-dot-home"></i>
          ${homeTeam} <strong>${homeProb}%</strong>
        </span>
        <span>
          <i class="v2-dot v2-dot-draw"></i>
          Draw <strong>${drawProb}%</strong>
        </span>
        <span>
          <i class="v2-dot v2-dot-away"></i>
          ${awayTeam} <strong>${awayProb}%</strong>
        </span>
      </div>

      <div class="v2-goals-row">
        <span>Expected goals: <strong>${pred.predictedHomeGoals.toFixed(2)}</strong> — <strong>${pred.predictedAwayGoals.toFixed(2)}</strong></span>
      </div>
    </article>
  `;
}
