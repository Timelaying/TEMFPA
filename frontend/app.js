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
});
