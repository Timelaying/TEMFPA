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

  const season = analysisForm.elements.season.value;
  const league = leagueSelect.options[leagueSelect.selectedIndex].text;
  feedback.textContent = secondTeam
    ? `${firstTeam} vs ${secondTeam} is ready to analyse for ${season}.`
    : `${firstTeam} is ready to analyse in the ${league}, ${season}.`;
  renderTeamDashboard({
    team: firstTeam,
    league: leagueSelect.value,
    leagueName: league,
    selectedSeason: season
  });
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

const getTeamHistory = (league, team) => seasonHistory[league]?.[team] || buildFallbackHistory(team);
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
  const width = 640;
  const height = 250;
  const padding = 34;
  const maxPosition = Math.max(20, ...history.map((item) => item.position));
  const points = history.map((item, index) => {
    const x = padding + (index * (width - padding * 2)) / (history.length - 1 || 1);
    const y = padding + ((item.position - 1) / (maxPosition - 1)) * (height - padding * 2);
    return { ...item, x, y };
  });
  const path = points.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ');
  positionChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">
    <g class="chart-grid">${[1, 5, 10, 15, 20].map((tick) => `<line x1="${padding}" x2="${width - padding}" y1="${padding + ((tick - 1) / (maxPosition - 1)) * (height - padding * 2)}" y2="${padding + ((tick - 1) / (maxPosition - 1)) * (height - padding * 2)}"></line><text x="4" y="${padding + ((tick - 1) / (maxPosition - 1)) * (height - padding * 2) + 4}">${ordinal(tick)}</text>`).join('')}</g>
    <path class="position-line" d="${path}"></path>
    ${points.map((point) => `<g class="position-point"><circle cx="${point.x}" cy="${point.y}" r="5"></circle><text x="${point.x}" y="${height - 7}">${point.season.slice(2)}</text><title>${point.season}: ${ordinal(point.position)}</title></g>`).join('')}
  </svg>`;
};

const renderResultsChart = ({ wins, draws, losses }) => {
  const total = wins + draws + losses;
  resultsTotal.textContent = `${total} matches`;
  resultsChart.innerHTML = [
    ['Wins', wins, 'wins'],
    ['Draws', draws, 'draws'],
    ['Losses', losses, 'losses']
  ].map(([label, value, className]) => `<div class="bar-row"><span>${label}</span><div><i class="${className}" style="width:${(value / total) * 100}%"></i></div><strong>${value}</strong></div>`).join('');
};

const renderTeamDashboard = ({ team, league, leagueName, selectedSeason }) => {
  const history = getTeamHistory(league, team);
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
  dashboardCopy.textContent = `${leagueName} dashboard for ${selectedSeason}, benchmarked against ${history[0].season}–${history.at(-1).season}.`;
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
  dashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
};
