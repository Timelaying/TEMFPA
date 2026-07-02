const header = document.querySelector('[data-header]');
const menuToggle = document.querySelector('[data-menu-toggle]');
const navigation = document.querySelector('[data-nav]');

const updateHeader = () => {
  header?.classList.toggle('scrolled', window.scrollY > 20);
};

updateHeader();
window.addEventListener('scroll', updateHeader, { passive: true });

menuToggle?.addEventListener('click', () => {
  const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!isOpen));
  menuToggle.setAttribute('aria-label', isOpen ? 'Open navigation' : 'Close navigation');
  navigation?.classList.toggle('open', !isOpen);
  document.body.classList.toggle('menu-open', !isOpen);
});

navigation?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    menuToggle?.setAttribute('aria-expanded', 'false');
    menuToggle?.setAttribute('aria-label', 'Open navigation');
    navigation.classList.remove('open');
    document.body.classList.remove('menu-open');
  });
});

const reveals = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  reveals.forEach((element) => revealObserver.observe(element));
} else {
  reveals.forEach((element) => element.classList.add('visible'));
}

document.querySelectorAll('[data-year]').forEach((element) => {
  element.textContent = new Date().getFullYear();
});

const leagueTeams = {
  'premier-league': [
    'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton & Hove Albion',
    'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds United',
    'Liverpool', 'Manchester City', 'Manchester United', 'Newcastle United',
    'Nottingham Forest', 'Sunderland', 'Tottenham Hotspur', 'West Ham United',
    'Wolverhampton Wanderers'
  ],
  'la-liga': [
    'Alavés', 'Athletic Club', 'Atlético Madrid', 'Barcelona', 'Celta Vigo', 'Elche',
    'Espanyol', 'Getafe', 'Girona', 'Levante', 'Mallorca', 'Osasuna', 'Rayo Vallecano',
    'Real Betis', 'Real Madrid', 'Real Oviedo', 'Real Sociedad', 'Sevilla', 'Valencia',
    'Villarreal'
  ],
  'serie-a': [
    'Atalanta', 'Bologna', 'Cagliari', 'Como', 'Cremonese', 'Fiorentina', 'Genoa',
    'Hellas Verona', 'Inter Milan', 'Juventus', 'Lazio', 'Lecce', 'AC Milan', 'Napoli',
    'Parma', 'Pisa', 'Roma', 'Sassuolo', 'Torino', 'Udinese'
  ],
  bundesliga: [
    'Augsburg', 'Bayer Leverkusen', 'Bayern Munich', 'Borussia Dortmund',
    'Borussia Mönchengladbach', 'Eintracht Frankfurt', 'FC Köln', 'Freiburg',
    'Hamburg', 'Heidenheim', 'Hoffenheim', 'Mainz 05', 'RB Leipzig', 'St. Pauli',
    'Union Berlin', 'VfB Stuttgart', 'Werder Bremen', 'Wolfsburg'
  ],
  'ligue-1': [
    'Angers', 'Auxerre', 'Brest', 'Le Havre', 'Lens', 'Lille', 'Lorient', 'Lyon',
    'Marseille', 'Metz', 'Monaco', 'Nantes', 'Nice', 'Paris FC',
    'Paris Saint-Germain', 'Rennes', 'Strasbourg', 'Toulouse'
  ]
};

const analysisForm = document.querySelector('[data-analysis-form]');
const leagueSelect = document.querySelector('[data-league-select]');
const seasonStartSelect = document.querySelector('[data-season-start]');
const seasonEndSelect = document.querySelector('[data-season-end]');
const teamComboboxes = [...document.querySelectorAll('[data-team-combobox]')];

const getInitials = (team) => team
  .split(/\s+/)
  .filter((word) => !['and', '&'].includes(word.toLowerCase()))
  .slice(0, 2)
  .map((word) => word[0])
  .join('')
  .toUpperCase();

const closeCombobox = (combobox) => {
  combobox.classList.remove('open');
  const input = combobox.querySelector('input');
  input.setAttribute('aria-expanded', 'false');
  combobox.querySelector('.team-options').hidden = true;
};

const setTeam = (combobox, team) => {
  const input = combobox.querySelector('input');
  input.value = team;
  input.dataset.selectedTeam = team;
  combobox.querySelector('.clear-team').hidden = false;
  combobox.closest('.team-field').classList.remove('invalid');
  combobox.closest('.team-field').querySelector('[data-field-error]').textContent = '';
  closeCombobox(combobox);
};

const renderTeamOptions = (combobox, query = '') => {
  const list = combobox.querySelector('.team-options');
  const teams = leagueTeams[leagueSelect?.value] || [];
  const normalizedQuery = query.trim().toLowerCase();
  const matches = teams.filter((team) => team.toLowerCase().includes(normalizedQuery));

  list.replaceChildren();
  if (!matches.length) {
    const emptyItem = document.createElement('li');
    emptyItem.className = 'no-options';
    emptyItem.textContent = 'No teams found';
    list.append(emptyItem);
  } else {
    matches.forEach((team) => {
      const option = document.createElement('li');
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.dataset.initials = getInitials(team);
      option.textContent = team;
      option.addEventListener('pointerdown', (event) => {
        event.preventDefault();
        setTeam(combobox, team);
      });
      list.append(option);
    });
  }

  list.hidden = false;
  combobox.classList.add('open');
  combobox.querySelector('input').setAttribute('aria-expanded', 'true');
};

teamComboboxes.forEach((combobox) => {
  const input = combobox.querySelector('input');
  const clearButton = combobox.querySelector('.clear-team');

  input.addEventListener('focus', () => renderTeamOptions(combobox, input.value));
  input.addEventListener('input', () => {
    delete input.dataset.selectedTeam;
    clearButton.hidden = !input.value;
    renderTeamOptions(combobox, input.value);
  });
  input.addEventListener('keydown', (event) => {
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !combobox.classList.contains('open')) {
      renderTeamOptions(combobox, input.value);
    }
    const options = [...combobox.querySelectorAll('[role="option"]')];
    const activeIndex = options.findIndex((option) => option.classList.contains('active'));

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const direction = event.key === 'ArrowDown' ? 1 : -1;
      const nextIndex = activeIndex < 0 ? (direction > 0 ? 0 : options.length - 1) : (activeIndex + direction + options.length) % options.length;
      options.forEach((option) => option.classList.remove('active'));
      options[nextIndex]?.classList.add('active');
      options[nextIndex]?.scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      setTeam(combobox, options[activeIndex].textContent);
    } else if (event.key === 'Escape') {
      closeCombobox(combobox);
    }
  });
  input.addEventListener('blur', () => {
    window.setTimeout(() => closeCombobox(combobox), 100);
  });
  clearButton.addEventListener('click', () => {
    input.value = '';
    delete input.dataset.selectedTeam;
    clearButton.hidden = true;
    input.focus();
    renderTeamOptions(combobox);
  });
});

leagueSelect?.addEventListener('change', () => {
  teamComboboxes.forEach((combobox) => {
    const input = combobox.querySelector('input');
    input.value = '';
    delete input.dataset.selectedTeam;
    combobox.querySelector('.clear-team').hidden = true;
    closeCombobox(combobox);
  });
});

document.addEventListener('pointerdown', (event) => {
  teamComboboxes.forEach((combobox) => {
    if (!combobox.contains(event.target)) closeCombobox(combobox);
  });
});

analysisForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  const feedback = analysisForm.querySelector('[data-form-feedback]');
  const firstCombobox = teamComboboxes[0];
  const firstInput = firstCombobox.querySelector('input');
  const secondInput = teamComboboxes[1].querySelector('input');
  const firstTeam = firstInput.dataset.selectedTeam;
  const secondTeam = secondInput.dataset.selectedTeam;

  if (!firstTeam) {
    const field = firstCombobox.closest('.team-field');
    field.classList.add('invalid');
    field.querySelector('[data-field-error]').textContent = 'Choose a team from the dropdown.';
    feedback.textContent = '';
    firstInput.focus();
    renderTeamOptions(firstCombobox, firstInput.value);
    return;
  }

  if (secondInput.value && !secondTeam) {
    const field = teamComboboxes[1].closest('.team-field');
    field.classList.add('invalid');
    field.querySelector('[data-field-error]').textContent = 'Choose a team from the dropdown or clear this field.';
    feedback.textContent = '';
    secondInput.focus();
    renderTeamOptions(teamComboboxes[1], secondInput.value);
    return;
  }

  if (firstTeam === secondTeam) {
    const field = teamComboboxes[1].closest('.team-field');
    field.classList.add('invalid');
    field.querySelector('[data-field-error]').textContent = 'Choose a different second team.';
    feedback.textContent = '';
    secondInput.focus();
    return;
  }

  const seasonRange = getSelectedSeasonRange();
  const selectedSeason = seasonRange.at(-1);
  const rangeLabel = formatSeasonRange(seasonRange);
  const league = leagueSelect.options[leagueSelect.selectedIndex].text;
  feedback.textContent = secondTeam
    ? `${firstTeam} vs ${secondTeam} is ready to analyse for ${rangeLabel}.`
    : `${firstTeam} is ready to analyse in the ${league}, ${rangeLabel}.`;
  renderTeamDashboard({
    team: firstTeam,
    league: leagueSelect.value,
    leagueName: league,
    selectedSeason,
    seasonRange
  });

  if (secondTeam) {
    renderHeadToHead({
      teamA: firstTeam,
      teamB: secondTeam,
      league: leagueSelect.value,
      leagueName: league,
      selectedSeason,
      seasonRange
    });
    renderMatchPrediction({
      teamA: firstTeam,
      teamB: secondTeam,
      league: leagueSelect.value,
      leagueName: league,
      selectedSeason,
      seasonRange
    });
  } else {
    hideHeadToHead();
    hideMatchPrediction();
  }
});


const headToHeadMeetings = {
  'premier-league': {
    'Liverpool|Manchester City': [
      { date: '2024-03-10', season: '2023/24', home: 'Liverpool', away: 'Manchester City', homeGoals: 1, awayGoals: 1 },
      { date: '2023-11-25', season: '2023/24', home: 'Manchester City', away: 'Liverpool', homeGoals: 1, awayGoals: 1 },
      { date: '2023-04-01', season: '2022/23', home: 'Manchester City', away: 'Liverpool', homeGoals: 4, awayGoals: 1 },
      { date: '2022-10-16', season: '2022/23', home: 'Liverpool', away: 'Manchester City', homeGoals: 1, awayGoals: 0 },
      { date: '2022-04-10', season: '2021/22', home: 'Manchester City', away: 'Liverpool', homeGoals: 2, awayGoals: 2 },
      { date: '2021-10-03', season: '2021/22', home: 'Liverpool', away: 'Manchester City', homeGoals: 2, awayGoals: 2 },
      { date: '2021-02-07', season: '2020/21', home: 'Liverpool', away: 'Manchester City', homeGoals: 1, awayGoals: 4 },
      { date: '2020-11-08', season: '2020/21', home: 'Manchester City', away: 'Liverpool', homeGoals: 1, awayGoals: 1 },
      { date: '2020-07-02', season: '2019/20', home: 'Manchester City', away: 'Liverpool', homeGoals: 4, awayGoals: 0 },
      { date: '2019-11-10', season: '2019/20', home: 'Liverpool', away: 'Manchester City', homeGoals: 3, awayGoals: 1 }
    ],
    'Arsenal|Manchester City': [
      { date: '2024-03-31', season: '2023/24', home: 'Manchester City', away: 'Arsenal', homeGoals: 0, awayGoals: 0 },
      { date: '2023-10-08', season: '2023/24', home: 'Arsenal', away: 'Manchester City', homeGoals: 1, awayGoals: 0 },
      { date: '2023-04-26', season: '2022/23', home: 'Manchester City', away: 'Arsenal', homeGoals: 4, awayGoals: 1 },
      { date: '2023-02-15', season: '2022/23', home: 'Arsenal', away: 'Manchester City', homeGoals: 1, awayGoals: 3 },
      { date: '2022-01-01', season: '2021/22', home: 'Arsenal', away: 'Manchester City', homeGoals: 1, awayGoals: 2 }
    ]
  }
};

const headToHead = document.querySelector('[data-head-to-head]');
const h2hTitle = document.querySelector('[data-h2h-title]');
const h2hCopy = document.querySelector('[data-h2h-copy]');
const h2hMatchup = document.querySelector('[data-h2h-matchup]');
const h2hSeason = document.querySelector('[data-h2h-season]');
const h2hTeamA = document.querySelector('[data-h2h-team-a]');
const h2hTeamB = document.querySelector('[data-h2h-team-b]');
const h2hTeamAWins = document.querySelector('[data-h2h-team-a-wins]');
const h2hTeamBWins = document.querySelector('[data-h2h-team-b-wins]');
const h2hDraws = document.querySelector('[data-h2h-draws]');
const h2hTotal = document.querySelector('[data-h2h-total]');
const h2hGoalsA = document.querySelector('[data-h2h-goals-a]');
const h2hGoalsB = document.querySelector('[data-h2h-goals-b]');
const h2hBiggest = document.querySelector('[data-h2h-biggest]');
const h2hChartTotal = document.querySelector('[data-h2h-chart-total]');
const h2hChart = document.querySelector('[data-h2h-chart]');
const h2hForm = document.querySelector('[data-h2h-form]');
const h2hTable = document.querySelector('[data-h2h-table]');

const pairKey = (teamA, teamB) => [teamA, teamB].sort().join('|');
const seasonOrder = ['2019/20', '2020/21', '2021/22', '2022/23', '2023/24'];

const getSelectedSeasonRange = () => {
  const startIndex = seasonOrder.indexOf(seasonStartSelect?.value);
  const endIndex = seasonOrder.indexOf(seasonEndSelect?.value);
  const safeStart = startIndex >= 0 ? startIndex : 0;
  const safeEnd = endIndex >= 0 ? endIndex : seasonOrder.length - 1;
  const [from, to] = safeStart <= safeEnd ? [safeStart, safeEnd] : [safeEnd, safeStart];
  return seasonOrder.slice(from, to + 1);
};

const formatSeasonRange = (seasons) => seasons.length === 1 ? seasons[0] : `${seasons[0]}–${seasons.at(-1)}`;

const buildFallbackMeetings = (teamA, teamB) => {
  const seed = [...`${teamA}${teamB}`].reduce((total, char) => total + char.charCodeAt(0), 0);
  return seasonOrder.flatMap((season, index) => [0, 1].map((leg) => {
    const teamAHome = (index + leg) % 2 === 0;
    const home = teamAHome ? teamA : teamB;
    const away = teamAHome ? teamB : teamA;
    const homeGoals = (seed + index + leg * 2) % 4;
    const awayGoals = (seed + index * 2 + leg) % 3;
    return { date: `${2020 + index}-${String(3 + leg * 7).padStart(2, '0')}-12`, season, home, away, homeGoals, awayGoals };
  }));
};

const getHeadToHeadMeetings = (league, teamA, teamB) => headToHeadMeetings[league]?.[pairKey(teamA, teamB)] || buildFallbackMeetings(teamA, teamB);
const getWinner = (meeting) => meeting.homeGoals === meeting.awayGoals ? 'Draw' : meeting.homeGoals > meeting.awayGoals ? meeting.home : meeting.away;
const outcomeForTeam = (meeting, team) => {
  const winner = getWinner(meeting);
  if (winner === 'Draw') return 'D';
  return winner === team ? 'W' : 'L';
};
const resultLabel = { W: 'win', D: 'draw', L: 'loss' };

const hideHeadToHead = () => {
  if (headToHead) headToHead.hidden = true;
};

const renderHeadToHead = ({ teamA, teamB, league, leagueName, selectedSeason, seasonRange }) => {
  const seasons = seasonRange?.length ? seasonRange : seasonOrder.slice(0, seasonOrder.indexOf(selectedSeason) + 1 || seasonOrder.length);
  const meetings = getHeadToHeadMeetings(league, teamA, teamB).filter((meeting) => seasons.includes(meeting.season));
  const orderedMeetings = [...meetings].sort((a, b) => b.date.localeCompare(a.date));
  const stats = meetings.reduce((acc, meeting) => {
    const winner = getWinner(meeting);
    if (winner === teamA) acc.teamAWins += 1;
    if (winner === teamB) acc.teamBWins += 1;
    if (winner === 'Draw') acc.draws += 1;
    acc.goalsA += meeting.home === teamA ? meeting.homeGoals : meeting.awayGoals;
    acc.goalsB += meeting.home === teamB ? meeting.homeGoals : meeting.awayGoals;
    const margin = Math.abs(meeting.homeGoals - meeting.awayGoals);
    if (winner !== 'Draw' && margin > acc.biggest.margin) acc.biggest = { margin, meeting, winner };
    return acc;
  }, { teamAWins: 0, teamBWins: 0, draws: 0, goalsA: 0, goalsB: 0, biggest: { margin: 0 } });

  headToHead.hidden = false;
  h2hTitle.textContent = `${teamA} vs ${teamB}`;
  h2hCopy.textContent = `${leagueName} head-to-head record across ${seasons[0]}–${seasons.at(-1)}.`;
  h2hMatchup.textContent = `${teamA} vs ${teamB}`;
  h2hSeason.textContent = `${seasons[0]}–${seasons.at(-1)}`;
  h2hTeamA.textContent = teamA;
  h2hTeamB.textContent = teamB;
  h2hTeamAWins.textContent = stats.teamAWins;
  h2hTeamBWins.textContent = stats.teamBWins;
  h2hDraws.textContent = stats.draws;
  h2hTotal.textContent = `${meetings.length} matches`;
  h2hGoalsA.textContent = stats.goalsA;
  h2hGoalsB.textContent = stats.goalsB;
  h2hBiggest.textContent = stats.biggest.meeting
    ? `Biggest win: ${stats.biggest.winner} ${stats.biggest.meeting.homeGoals}–${stats.biggest.meeting.awayGoals} (${stats.biggest.meeting.home} vs ${stats.biggest.meeting.away}, ${stats.biggest.meeting.season})`
    : 'Biggest win: N/A';

  h2hChartTotal.textContent = `${meetings.length} matches`;
  renderChart('h2h', h2hChart, {
    type: 'doughnut',
    data: {
      labels: [teamA, 'Draws', teamB],
      datasets: [{
        data: [stats.teamAWins, stats.draws, stats.teamBWins],
        backgroundColor: [chartPalette.green, chartPalette.grey, chartPalette.purple],
        borderColor: '#0b1d16',
        borderWidth: 4,
        hoverOffset: 8
      }]
    },
    options: baseChartOptions({
      cutout: '62%',
      scales: {},
      plugins: { ...baseChartOptions().plugins, legend: { position: 'bottom', labels: { color: chartPalette.text, boxWidth: 11, usePointStyle: true } } }
    })
  });

  h2hForm.innerHTML = [teamA, teamB].map((team) => `<div class="h2h-form-row"><span>${team}</span>${orderedMeetings.slice(0, 5).map((meeting) => {
    const outcome = outcomeForTeam(meeting, team);
    return `<i class="result ${resultLabel[outcome]}" title="${meeting.home} ${meeting.homeGoals}–${meeting.awayGoals} ${meeting.away}">${outcome}</i>`;
  }).join('')}</div>`).join('');

  h2hTable.innerHTML = orderedMeetings.slice(0, 5).map((meeting) => `<tr><td>${new Date(meeting.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</td><td>${meeting.season}</td><td>${meeting.home} vs ${meeting.away}</td><td>${meeting.homeGoals}–${meeting.awayGoals}</td><td>${getWinner(meeting)}</td></tr>`).join('');
  tableRows = normalizeTableRows(orderedMeetings.map((meeting) => ({ ...meeting, winner: getWinner(meeting), leaguePosition: '—', points: '—' })));
  tablePage = 1;
  renderDataTable();
  headToHead.scrollIntoView({ behavior: 'smooth', block: 'start' });
};


const matchPrediction = document.querySelector('[data-match-prediction]');
const predictionTitle = document.querySelector('[data-prediction-title]');
const predictionCopy = document.querySelector('[data-prediction-copy]');
const predictedWinner = document.querySelector('[data-predicted-winner]');
const confidenceLevel = document.querySelector('[data-confidence-level]');
const predictionSummary = document.querySelector('[data-prediction-summary]');
const probabilityHeading = document.querySelector('[data-probability-heading]');
const confidenceBadge = document.querySelector('[data-confidence-badge]');
const predictionBars = document.querySelector('[data-prediction-bars]');
const predictionExplanation = document.querySelector('[data-prediction-explanation]');

const hideMatchPrediction = () => {
  if (matchPrediction) matchPrediction.hidden = true;
};

const predictionActionStatus = document.querySelector('[data-save-status]');
const generatePredictionButton = document.querySelector('[data-generate-prediction]');
const exportResultButton = document.querySelector('[data-export-result]');
const saveResultButton = document.querySelector('[data-save-result]');

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const teamStrength = (league, team, selectedSeason, seasonRange) => {
  const history = getTeamHistory(league, team);
  const scopedHistory = seasonRange?.length ? history.filter((item) => seasonRange.includes(item.season)) : history.slice(0, seasonOrder.indexOf(selectedSeason) + 1);
  const recentHistory = scopedHistory.slice(-3);
  const latest = scopedHistory.at(-1);
  const averagePosition = recentHistory.reduce((sum, item) => sum + item.position, 0) / recentHistory.length;
  const goalDifference = recentHistory.reduce((sum, item) => sum + item.goalsFor - item.goalsAgainst, 0) / recentHistory.length;
  const pointsPerMatch = recentHistory.reduce((sum, item) => sum + item.wins * 3 + item.draws, 0) / (recentHistory.length * 38);

  return {
    latest,
    averagePosition,
    goalDifference,
    pointsPerMatch,
    score: (21 - averagePosition) * 2.2 + goalDifference * 0.28 + pointsPerMatch * 24
  };
};

const buildPrediction = ({ teamA, teamB, league, selectedSeason, seasonRange }) => {
  const a = teamStrength(league, teamA, selectedSeason, seasonRange);
  const b = teamStrength(league, teamB, selectedSeason, seasonRange);
  const meetings = getHeadToHeadMeetings(league, teamA, teamB);
  const seasons = seasonRange?.length ? seasonRange : seasonOrder.slice(0, seasonOrder.indexOf(selectedSeason) + 1 || seasonOrder.length);
  const scopedMeetings = meetings.filter((meeting) => seasons.includes(meeting.season));
  const h2hBalance = scopedMeetings.reduce((sum, meeting) => {
    const winner = getWinner(meeting);
    if (winner === teamA) return sum + 1.5;
    if (winner === teamB) return sum - 1.5;
    return sum;
  }, 0);
  const scoreDiff = a.score - b.score + h2hBalance;
  const drawProbability = clamp(28 - Math.abs(scoreDiff) * 0.45, 16, 31);
  const decisivePool = 100 - drawProbability;
  const teamAProbability = clamp(decisivePool * (0.5 + scoreDiff / 90), 8, decisivePool - 8);
  const teamBProbability = 100 - drawProbability - teamAProbability;
  const probabilities = [
    { label: teamA, value: Math.round(teamAProbability), className: 'team-a' },
    { label: 'Draw', value: Math.round(drawProbability), className: 'draw' },
    { label: teamB, value: Math.round(teamBProbability), className: 'team-b' }
  ];
  const leader = probabilities.reduce((best, item) => item.value > best.value ? item : best, probabilities[0]);
  const sorted = [...probabilities].sort((left, right) => right.value - left.value);
  const margin = sorted[0].value - sorted[1].value;
  const confidence = margin >= 18 ? 'High' : margin >= 9 ? 'Medium' : 'Low';

  return { a, b, scopedMeetings, probabilities, leader, confidence, margin };
};

let latestPredictionResult = null;

const renderMatchPrediction = ({ teamA, teamB, league, leagueName, selectedSeason, seasonRange }) => {
  const prediction = buildPrediction({ teamA, teamB, league, selectedSeason, seasonRange });
  const rangeLabel = formatSeasonRange(seasonRange?.length ? seasonRange : [selectedSeason]);

  matchPrediction.hidden = false;
  predictionTitle.textContent = `${teamA} vs ${teamB} prediction`;
  predictionCopy.textContent = `${leagueName} prediction for ${rangeLabel}, based on backend-style analysis signals from recent performance, goals, and head-to-head records.`;
  predictedWinner.textContent = prediction.leader.label === 'Draw' ? 'Draw' : prediction.leader.label;
  confidenceLevel.textContent = `${prediction.confidence} confidence`;
  confidenceBadge.textContent = `${prediction.confidence} confidence`;
  predictionSummary.textContent = `${prediction.leader.label} is the most likely outcome at ${prediction.leader.value}%.`;
  probabilityHeading.textContent = `${teamA} / Draw / ${teamB}`;
  renderChart('prediction', predictionBars, {
    type: 'bar',
    data: {
      labels: prediction.probabilities.map((item) => item.label),
      datasets: [{
        label: 'Outcome probability',
        data: prediction.probabilities.map((item) => item.value),
        backgroundColor: [chartPalette.green, chartPalette.grey, chartPalette.purple],
        borderRadius: 12,
        borderSkipped: false
      }]
    },
    options: baseChartOptions({
      plugins: { ...baseChartOptions().plugins, legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: chartPalette.text, font: { weight: 800 } } },
        y: { beginAtZero: true, max: 100, grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, callback: (value) => `${value}%` } }
      }
    })
  });
  latestPredictionResult = { teamA, teamB, leagueName, seasonRange: rangeLabel, winner: prediction.leader.label, confidence: prediction.confidence, probabilities: prediction.probabilities };
  predictionExplanation.textContent = `${teamA} carries an average recent league position of ${prediction.a.averagePosition.toFixed(1)} and an average goal difference of ${prediction.a.goalDifference.toFixed(1)}, while ${teamB} posts ${prediction.b.averagePosition.toFixed(1)} and ${prediction.b.goalDifference.toFixed(1)}. The model also reviews ${prediction.scopedMeetings.length} head-to-head meetings in the selected range, then converts those signals into win and draw probabilities. A ${prediction.margin}-point gap between the top two outcomes produces a ${prediction.confidence.toLowerCase()} confidence level.`;
};

const getPredictionPayload = () => latestPredictionResult ? {
  ...latestPredictionResult,
  generatedAt: new Date().toISOString()
} : null;

const setPredictionActionStatus = (message) => {
  if (predictionActionStatus) predictionActionStatus.textContent = message;
};

generatePredictionButton?.addEventListener('click', () => {
  if (!latestPredictionResult) {
    setPredictionActionStatus('Choose two teams first.');
    return;
  }
  setPredictionActionStatus('Prediction generated from the latest comparison.');
  predictionExplanation?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

exportResultButton?.addEventListener('click', () => {
  const payload = getPredictionPayload();
  if (!payload) {
    setPredictionActionStatus('Choose two teams before exporting.');
    return;
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `temfpa-${payload.teamA}-vs-${payload.teamB}-${payload.seasonRange}.json`.replace(/[^a-z0-9.]+/gi, '-').toLowerCase();
  link.click();
  URL.revokeObjectURL(url);
  setPredictionActionStatus('Result exported as JSON.');
});

saveResultButton?.addEventListener('click', () => {
  const payload = getPredictionPayload();
  if (!payload) {
    setPredictionActionStatus('Choose two teams before saving.');
    return;
  }
  localStorage.setItem('temfpa:lastPrediction', JSON.stringify(payload));
  setPredictionActionStatus('Result saved in this browser.');
});

const seasonHistory = {
  'premier-league': {
    'Manchester City': [
      { season: '2019/20', position: 2, wins: 26, draws: 3, losses: 9, goalsFor: 102, goalsAgainst: 35 },
      { season: '2020/21', position: 1, wins: 27, draws: 5, losses: 6, goalsFor: 83, goalsAgainst: 32 },
      { season: '2021/22', position: 1, wins: 29, draws: 6, losses: 3, goalsFor: 99, goalsAgainst: 26 },
      { season: '2022/23', position: 1, wins: 28, draws: 5, losses: 5, goalsFor: 94, goalsAgainst: 33 },
      { season: '2023/24', position: 1, wins: 28, draws: 7, losses: 3, goalsFor: 96, goalsAgainst: 34 }
    ],
    Arsenal: [
      { season: '2019/20', position: 8, wins: 14, draws: 14, losses: 10, goalsFor: 56, goalsAgainst: 48 },
      { season: '2020/21', position: 8, wins: 18, draws: 7, losses: 13, goalsFor: 55, goalsAgainst: 39 },
      { season: '2021/22', position: 5, wins: 22, draws: 3, losses: 13, goalsFor: 61, goalsAgainst: 48 },
      { season: '2022/23', position: 2, wins: 26, draws: 6, losses: 6, goalsFor: 88, goalsAgainst: 43 },
      { season: '2023/24', position: 2, wins: 28, draws: 5, losses: 5, goalsFor: 91, goalsAgainst: 29 }
    ],
    Liverpool: [
      { season: '2019/20', position: 1, wins: 32, draws: 3, losses: 3, goalsFor: 85, goalsAgainst: 33 },
      { season: '2020/21', position: 3, wins: 20, draws: 9, losses: 9, goalsFor: 68, goalsAgainst: 42 },
      { season: '2021/22', position: 2, wins: 28, draws: 8, losses: 2, goalsFor: 94, goalsAgainst: 26 },
      { season: '2022/23', position: 5, wins: 19, draws: 10, losses: 9, goalsFor: 75, goalsAgainst: 47 },
      { season: '2023/24', position: 3, wins: 24, draws: 10, losses: 4, goalsFor: 86, goalsAgainst: 41 }
    ]
  }
};

const buildFallbackHistory = (team) => {
  const seed = [...team].reduce((total, char) => total + char.charCodeAt(0), 0);
  return ['2019/20', '2020/21', '2021/22', '2022/23', '2023/24'].map((season, index) => {
    const position = ((seed + index * 7) % 17) + 1;
    const wins = Math.max(6, 24 - position + (index % 3));
    const draws = 5 + ((seed + index) % 7);
    const losses = Math.max(3, 38 - wins - draws);
    return {
      season,
      position,
      wins,
      draws,
      losses,
      goalsFor: 42 + wins * 2 + (seed % 9),
      goalsAgainst: 25 + losses * 2 + ((seed + index) % 8)
    };
  });
};

const dashboard = document.querySelector('[data-team-dashboard]');
const dashboardTitle = document.querySelector('[data-dashboard-title]');
const dashboardCopy = document.querySelector('[data-dashboard-copy]');
const dashboardSummary = document.querySelector('[data-dashboard-summary]');
const positionChart = document.querySelector('[data-position-chart]');
const resultsChart = document.querySelector('[data-results-chart]');
const resultsTotal = document.querySelector('[data-results-total]');
const goalsChart = document.querySelector('[data-goals-chart]');
const goalsBalance = document.querySelector('[data-goals-balance]');
const formChart = document.querySelector('[data-form-chart]');

const getTeamHistory = (league, team) => seasonHistory[league]?.[team] || buildFallbackHistory(team);

const tableSearch = document.querySelector('[data-table-search]');
const tableFilter = document.querySelector('[data-table-filter]');
const resultsTable = document.querySelector('[data-results-table]');
const resultsTableBody = document.querySelector('[data-results-table-body]');
const tableCount = document.querySelector('[data-table-count]');
const pageStatus = document.querySelector('[data-page-status]');
const pagePrev = document.querySelector('[data-page-prev]');
const pageNext = document.querySelector('[data-page-next]');
const tablePageSize = 5;
let tableRows = [];
let tablePage = 1;
let tableSort = { key: 'date', direction: 'desc' };

const pointsForSeason = ({ wins = 0, draws = 0 }) => wins * 3 + draws;

const buildTeamMatchRows = ({ team, league, selectedSeason, seasonRange }) => {
  const history = getTeamHistory(league, team);
  const seasons = seasonRange?.length ? seasonRange : seasonOrder.slice(0, seasonOrder.indexOf(selectedSeason) + 1 || seasonOrder.length);
  return seasons.flatMap((season, index) => {
    const standings = history.find((item) => item.season === season) || history[index] || history.at(-1);
    const opponents = (leagueTeams[league] || []).filter((candidate) => candidate !== team);
    return opponents.slice(0, 2).map((opponent, leg) => {
      const homeTeam = (index + leg) % 2 === 0 ? team : opponent;
      const awayTeam = homeTeam === team ? opponent : team;
      const homeGoals = homeTeam === team ? (standings.wins + index + leg) % 4 : (standings.losses + leg) % 3;
      const awayGoals = awayTeam === team ? (standings.wins + leg) % 4 : (standings.draws + index) % 3;
      return {
        season,
        date: `${2020 + index}-${String(8 + leg * 5).padStart(2, '0')}-18`,
        home: homeTeam,
        away: awayTeam,
        homeGoals,
        awayGoals,
        winner: homeGoals === awayGoals ? 'Draw' : homeGoals > awayGoals ? homeTeam : awayTeam,
        leaguePosition: standings.position,
        points: pointsForSeason(standings)
      };
    });
  });
};

const normalizeTableRows = (rows) => rows.map((row) => ({
  ...row,
  leaguePosition: row.leaguePosition ?? '—',
  points: row.points ?? '—'
}));

const renderDataTable = () => {
  if (!resultsTableBody) return;
  const query = tableSearch?.value.trim().toLowerCase() || '';
  const filter = tableFilter?.value || 'all';
  const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });
  const filtered = tableRows.filter((row) => {
    const matchesTeam = !query || row.home.toLowerCase().includes(query) || row.away.toLowerCase().includes(query);
    const matchesFilter = filter === 'all' || (filter === 'draws' ? row.winner === 'Draw' : row.winner !== 'Draw');
    return matchesTeam && matchesFilter;
  }).sort((a, b) => {
    const result = collator.compare(String(a[tableSort.key]), String(b[tableSort.key]));
    return tableSort.direction === 'asc' ? result : -result;
  });
  const totalPages = Math.max(1, Math.ceil(filtered.length / tablePageSize));
  tablePage = Math.min(tablePage, totalPages);
  const pageRows = filtered.slice((tablePage - 1) * tablePageSize, tablePage * tablePageSize);
  resultsTableBody.innerHTML = pageRows.map((row) => `
    <tr>
      <td data-label="Season">${row.season}</td>
      <td data-label="Date">${new Date(row.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
      <td data-label="Home team">${row.home}</td>
      <td data-label="Away team">${row.away}</td>
      <td data-label="Home score">${row.homeGoals}</td>
      <td data-label="Away score">${row.awayGoals}</td>
      <td data-label="Winner">${row.winner}</td>
      <td data-label="League position">${row.leaguePosition}</td>
      <td data-label="Points">${row.points}</td>
    </tr>
  `).join('') || '<tr><td colspan="9">No table rows match the current filters.</td></tr>';
  tableCount.textContent = `${filtered.length} result${filtered.length === 1 ? '' : 's'}`;
  pageStatus.textContent = `Page ${tablePage} of ${totalPages}`;
  pagePrev.disabled = tablePage === 1;
  pageNext.disabled = tablePage === totalPages;
};

resultsTable?.querySelectorAll('[data-sort-key]').forEach((button) => {
  button.addEventListener('click', () => {
    const key = button.dataset.sortKey;
    tableSort = { key, direction: tableSort.key === key && tableSort.direction === 'asc' ? 'desc' : 'asc' };
    tablePage = 1;
    renderDataTable();
  });
});
tableSearch?.addEventListener('input', () => { tablePage = 1; renderDataTable(); });
tableFilter?.addEventListener('change', () => { tablePage = 1; renderDataTable(); });
pagePrev?.addEventListener('click', () => { tablePage -= 1; renderDataTable(); });
pageNext?.addEventListener('click', () => { tablePage += 1; renderDataTable(); });


const chartInstances = new Map();
const chartPalette = {
  green: '#69f0ae',
  greenDark: '#22d682',
  purple: '#a98af5',
  amber: '#ffb451',
  grey: '#aebdb7',
  red: '#ff7979',
  grid: 'rgba(255,255,255,.08)',
  text: '#9fb5ab'
};

const getCanvas = (container) => container?.querySelector('canvas');

const renderChart = (key, container, config) => {
  const canvas = getCanvas(container);
  if (!canvas || !window.Chart) {
    if (container) container.innerHTML = '<p class="chart-fallback">Chart library unavailable. Please refresh when online.</p>';
    return;
  }
  chartInstances.get(key)?.destroy();
  chartInstances.set(key, new Chart(canvas, config));
};

const baseChartOptions = (overrides = {}) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: chartPalette.text, boxWidth: 11, boxHeight: 11, usePointStyle: true } },
    tooltip: { backgroundColor: '#06130f', borderColor: 'rgba(105,240,174,.25)', borderWidth: 1, titleColor: '#fff', bodyColor: '#d6e2dd' }
  },
  scales: {
    x: { grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, font: { weight: 700 } } },
    y: { grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, font: { weight: 700 } } }
  },
  ...overrides
});

const ordinal = (value) => `${value}${['th', 'st', 'nd', 'rd'][value % 100 > 10 && value % 100 < 14 ? 0 : value % 10] || 'th'}`;

const renderSummaryCards = (metrics) => {
  dashboardSummary.replaceChildren(...metrics.map(({ label, value, detail }) => {
    const card = document.createElement('article');
    card.className = 'summary-card';
    card.innerHTML = `<span>${label}</span><strong>${value}</strong><small>${detail}</small>`;
    return card;
  }));
};

const renderPositionChart = (history) => {
  renderChart('position', positionChart, {
    type: 'line',
    data: {
      labels: history.map((item) => item.season),
      datasets: [{
        label: 'League position',
        data: history.map((item) => item.position),
        borderColor: chartPalette.green,
        backgroundColor: 'rgba(105,240,174,.16)',
        fill: true,
        tension: 0.35,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointBackgroundColor: '#0b1d16',
        pointBorderColor: chartPalette.green,
        pointBorderWidth: 3
      }]
    },
    options: baseChartOptions({
      scales: {
        x: { grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, font: { weight: 700 } } },
        y: { reverse: true, min: 1, suggestedMax: 20, grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, callback: (value) => ordinal(value), stepSize: 2 } }
      }
    })
  });
};

const renderResultsChart = ({ wins, draws, losses }) => {
  const total = wins + draws + losses;
  resultsTotal.textContent = `${total} matches`;
  renderChart('results', resultsChart, {
    type: 'bar',
    data: {
      labels: ['Wins', 'Draws', 'Losses'],
      datasets: [{
        label: 'Match outcomes',
        data: [wins, draws, losses],
        backgroundColor: [chartPalette.green, chartPalette.grey, chartPalette.red],
        borderRadius: 12,
        borderSkipped: false
      }]
    },
    options: baseChartOptions({
      indexAxis: 'y',
      plugins: { ...baseChartOptions().plugins, legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text, precision: 0 } },
        y: { grid: { display: false }, ticks: { color: chartPalette.text, font: { weight: 800 } } }
      }
    })
  });
};

const renderGoalsChart = (history) => {
  const goalsFor = history.reduce((sum, item) => sum + item.goalsFor, 0);
  const goalsAgainst = history.reduce((sum, item) => sum + item.goalsAgainst, 0);
  goalsBalance.textContent = `${goalsFor - goalsAgainst > 0 ? '+' : ''}${goalsFor - goalsAgainst} GD`;
  renderChart('goals', goalsChart, {
    type: 'bar',
    data: {
      labels: history.map((item) => item.season),
      datasets: [
        { label: 'Goals scored', data: history.map((item) => item.goalsFor), backgroundColor: chartPalette.green, borderRadius: 8 },
        { label: 'Goals conceded', data: history.map((item) => item.goalsAgainst), backgroundColor: chartPalette.purple, borderRadius: 8 }
      ]
    },
    options: baseChartOptions({ scales: { x: { grid: { display: false }, ticks: { color: chartPalette.text } }, y: { beginAtZero: true, grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text } } } })
  });
};

const renderFormChart = (history) => {
  const recent = history.slice(-5);
  renderChart('form', formChart, {
    type: 'line',
    data: {
      labels: recent.map((item) => item.season),
      datasets: [{
        label: 'Points',
        data: recent.map(pointsForSeason),
        borderColor: chartPalette.amber,
        backgroundColor: 'rgba(255,180,81,.18)',
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointBackgroundColor: chartPalette.amber
      }]
    },
    options: baseChartOptions({ scales: { x: { grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text } }, y: { beginAtZero: true, suggestedMax: 100, grid: { color: chartPalette.grid }, ticks: { color: chartPalette.text } } } })
  });
};

const renderTeamDashboard = ({ team, league, leagueName, selectedSeason, seasonRange }) => {
  const fullHistory = getTeamHistory(league, team);
  const history = seasonRange?.length ? fullHistory.filter((item) => seasonRange.includes(item.season)) : fullHistory;
  const selected = history.find((item) => item.season === selectedSeason) || history.at(-1);
  const previous = history[history.indexOf(selected) - 1];
  const best = history.reduce((bestItem, item) => item.position < bestItem.position ? item : bestItem, history[0]);
  const worst = history.reduce((worstItem, item) => item.position > worstItem.position ? item : worstItem, history[0]);
  const totals = history.reduce((acc, item) => ({
    wins: acc.wins + item.wins,
    draws: acc.draws + item.draws,
    losses: acc.losses + item.losses,
    goalsFor: acc.goalsFor + item.goalsFor,
    goalsAgainst: acc.goalsAgainst + item.goalsAgainst
  }), { wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 });
  const average = history.reduce((sum, item) => sum + item.position, 0) / history.length;

  dashboard.hidden = false;
  dashboardTitle.textContent = `${team} historical performance`;
  dashboardCopy.textContent = `${leagueName} dashboard for ${formatSeasonRange(history.map((item) => item.season))}, benchmarked across the selected season range.`;
  renderSummaryCards([
    { label: 'Selected season position', value: ordinal(selected.position), detail: selected.season },
    { label: 'Previous season position', value: previous ? ordinal(previous.position) : 'N/A', detail: previous?.season || 'No earlier season' },
    { label: 'Best finish in range', value: ordinal(best.position), detail: best.season },
    { label: 'Worst finish in range', value: ordinal(worst.position), detail: worst.season },
    { label: 'Average league position', value: average.toFixed(1), detail: `${history.length} seasons` },
    { label: 'Wins / Draws / Losses', value: `${totals.wins}/${totals.draws}/${totals.losses}`, detail: 'Available match totals' },
    { label: 'Goals scored', value: totals.goalsFor, detail: 'Across selected range' },
    { label: 'Goals conceded', value: totals.goalsAgainst, detail: 'Across selected range' }
  ]);
  renderPositionChart(history);
  renderResultsChart(totals);
  renderGoalsChart(history);
  renderFormChart(history);
  tableRows = normalizeTableRows(buildTeamMatchRows({ team, league, selectedSeason, seasonRange }));
  tablePage = 1;
  renderDataTable();
  dashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
};
