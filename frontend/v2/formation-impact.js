/**
 * Renders the formation impact table.
 */
export function renderFormationImpact(formationImpact, container) {
  if (!formationImpact) {
    container.innerHTML = '';
    return;
  }

  const homeFormation = formationImpact.homeFormation || 'Unknown';
  const awayFormation = formationImpact.awayFormation || 'Unknown';
  const homeWinPct = formationImpact.homeFormationWinPercent != null
    ? `${formationImpact.homeFormationWinPercent.toFixed(1)}%`
    : 'N/A';
  const awayWinPct = formationImpact.awayFormationWinPercent != null
    ? `${formationImpact.awayFormationWinPercent.toFixed(1)}%`
    : 'N/A';

  container.innerHTML = `
    <div class="v2-formation-section">
      <h3 class="v2-section-title">Formation Impact</h3>
      <table class="v2-formation-table">
        <thead>
          <tr>
            <th>Team</th>
            <th>Formation</th>
            <th>Win % with formation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Home</td>
            <td><span class="v2-formation-badge">${homeFormation}</span></td>
            <td>${homeWinPct}</td>
          </tr>
          <tr>
            <td>Away</td>
            <td><span class="v2-formation-badge">${awayFormation}</span></td>
            <td>${awayWinPct}</td>
          </tr>
        </tbody>
      </table>
      <p class="v2-formation-comment">${formationImpact.formationComment}</p>
    </div>
  `;
}
