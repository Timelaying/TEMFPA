/**
 * Renders top scoreline probability cards side by side.
 */
export function renderScorelines(topScorelines, container) {
  if (!topScorelines || topScorelines.length === 0) {
    container.innerHTML = '<p class="v2-empty">No scoreline predictions available.</p>';
    return;
  }

  const cards = topScorelines.map((sl, i) => {
    const pct = (sl.probability * 100).toFixed(1);
    const rankLabel = i === 0 ? 'Most likely' : i === 1 ? '2nd most likely' : '3rd most likely';
    return `
      <div class="v2-scoreline-card ${i === 0 ? 'v2-scoreline-top' : ''}">
        <span class="v2-scoreline-rank">${rankLabel}</span>
        <strong class="v2-scoreline-score">${sl.score}</strong>
        <span class="v2-scoreline-prob">${pct}%</span>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="v2-scorelines-section">
      <h3 class="v2-section-title">Top Scorelines</h3>
      <div class="v2-scorelines-grid">${cards}</div>
    </div>
  `;
}
