/**
 * Renders the player impact table showing absences and their effect.
 */
export function renderPlayerImpact(playerImpact, container) {
  if (!playerImpact || playerImpact.length === 0) {
    container.innerHTML = '<p class="v2-empty">No player absence data available.</p>';
    return;
  }

  const rows = playerImpact.map(entry => `
    <tr>
      <td>${entry.playerName}</td>
      <td>${entry.team}</td>
      <td><span class="v2-status-badge v2-status-${entry.status.toLowerCase().replace(/\s+/g, '-')}">${entry.status}</span></td>
      <td>${entry.teamWinPercentWithPlayer.toFixed(1)}%</td>
      <td>${entry.teamWinPercentWithoutPlayer.toFixed(1)}%</td>
      <td class="v2-impact-comment">${entry.impactComment}</td>
    </tr>
  `).join('');

  container.innerHTML = `
    <div class="v2-player-impact-section">
      <h3 class="v2-section-title">Player Availability Impact</h3>
      <div class="v2-table-wrap">
        <table class="v2-player-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Team</th>
              <th>Status</th>
              <th>Win% with player</th>
              <th>Win% without player</th>
              <th>Comment</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}
