/* ── Constants ────────────────────────────────────────────────────────── */
const API = {
  search:        '/api/search',
  generate:      '/api/generate',
  debugRaw:      '/api/debug-raw',
  refreshRoster: '/api/refresh-roster',
  exportCsv:     '/api/export/csv',
  exportExcel:   '/api/export/excel',
  bulkGenerate:  '/api/bulk-generate',
};

const NBA_TEAMS = [
  'ATL','BOS','BKN','CHA','CHI','CLE','DAL','DEN','DET','GSW',
  'HOU','IND','LAC','LAL','MEM','MIA','MIL','MIN','NOP','NYK',
  'OKC','ORL','PHI','PHX','POR','SAC','SAS','TOR','UTA','WAS',
];

const CATEGORIES = {
  'Shooting':            ['Shot','Touch','Shot Close','Shot Under','Shot Close Left','Shot Close Middle','Shot Close Right','Shot Mid','Spot-Up Shot Mid','Off-Screen Mid','Shot Mid Left','Shot Mid Left-Center','Shot Mid Center','Shot Mid Right-Center','Shot Mid Right','Shot Three','Spot-Up Three','Off-Screen Three','Shot Three Left','Shot Three Left-Center','Shot Three Center','Shot Three Right-Center','Shot Three Right','Contested Jumper Mid','Contested Jumper Three'],
  'Pull-Up & Step-Back': ['Step-Back Jumper Mid','Step-Back Jumper Three','Spin Jumper','Transition Pull-Up Three','Dribble Pull-Up Mid','Dribble Pull-Up Three'],
  'Driving':             ['Drive','Spot-Up Drive','Off-Screen Drive'],
  'Finishing':           ['Use Glass','Driving Layup','Step Through Shot','Spin Layup','Eurostep Layup','Hop Step Layup','Floater'],
  'Dunks':               ['Stand & Dunk','Drive & Dunk','Flashy Dunk','Alley-Oop','Putback','Crash'],
  'Direction & Triple Threat': ['Drive Right','Triple Threat Pump Fake','Triple Threat Jab Step','Triple Threat Idle','Triple Threat Shoot'],
  'Dribble Setup':       ['Set Up with Size Up','Set Up with Hesitation','No Set Up Dribble','Drive and Crossover','Drive and Double Crossover','Drive and Spin','Drive and Half Spin','Drive and Step Back','Drive and Behind the Back','Drive and Dribble Hesitation','Drive and In and Out','No Drive & Dribble Move'],
  'Passing & Balance':   ['Attack Strong on Drive','Dish to Open Man','Flashy Pass','Alley-Oop Pass','Roll vs Pop','Transition Spot Up vs Cut to Basket'],
  'Isolation':           ['Isolation vs Elite','Isolation vs Good','Isolation vs Average','Isolation vs Poor','Play Discipline'],
  'Post':                ['Post Up','Post Back Down','Post Aggressive Back Down','Post Face Up','Post Spin','Post Drive','Post Drop Step','Shoot From Post','Post Hook Left','Post Hook Right','Post Fade Left','Post Fade Right','Post Shimmy Shot','Post Hop Shot','Post Step Back Shot','Post Up and Under'],
  'Defense':             ['Takes Charge','Foul','Hard Foul','Pass Interception','On-Ball Steal','Blocked Shot','Contest Shot'],
};

// Hard caps (mirrors engine/constants.py)
const HARD_CAPS = {
  'Shot':75,'Touch':65,'Shot Close':60,'Shot Under':60,
  'Shot Close Left':50,'Shot Close Middle':50,'Shot Close Right':50,
  'Shot Mid':55,'Spot-Up Shot Mid':45,'Off-Screen Mid':40,
  'Shot Mid Left':45,'Shot Mid Left-Center':45,'Shot Mid Center':45,'Shot Mid Right-Center':45,'Shot Mid Right':45,
  'Shot Three':60,'Spot-Up Three':60,'Off-Screen Three':55,
  'Shot Three Left':50,'Shot Three Left-Center':50,'Shot Three Center':50,'Shot Three Right-Center':50,'Shot Three Right':50,
  'Contested Jumper Mid':45,'Contested Jumper Three':40,
  'Step-Back Jumper Mid':40,'Step-Back Jumper Three':35,'Spin Jumper':45,
  'Transition Pull-Up Three':45,'Dribble Pull-Up Mid':50,'Dribble Pull-Up Three':40,
  'Drive':60,'Spot-Up Drive':55,'Off-Screen Drive':50,'Use Glass':55,'Driving Layup':60,
  'Step Through Shot':45,'Spin Layup':55,'Eurostep Layup':55,'Hop Step Layup':55,
  'Floater':55,'Stand & Dunk':60,'Drive & Dunk':60,'Flashy Dunk':55,'Alley-Oop':55,
  'Putback':55,'Crash':55,'Drive Right':80,'Triple Threat Pump Fake':60,
  'Triple Threat Jab Step':60,'Triple Threat Idle':40,'Triple Threat Shoot':55,
  'Set Up with Size Up':55,'Set Up with Hesitation':55,'No Set Up Dribble':35,
  'Drive and Crossover':55,'Drive and Double Crossover':55,'Drive and Spin':55,
  'Drive and Half Spin':55,'Drive and Step Back':55,'Drive and Behind the Back':55,
  'Drive and Dribble Hesitation':55,'Drive and In and Out':55,'No Drive & Dribble Move':85,
  'Attack Strong on Drive':60,'Dish to Open Man':55,'Flashy Pass':55,'Alley-Oop Pass':55,
  'Roll vs Pop':85,'Transition Spot Up vs Cut to Basket':85,'Isolation vs Elite':55,
  'Isolation vs Good':55,'Isolation vs Average':55,'Isolation vs Poor':55,'Play Discipline':75,
  'Post Up':60,'Post Back Down':60,'Post Aggressive Back Down':60,'Post Face Up':55,
  'Post Spin':60,'Post Drive':60,'Post Drop Step':60,'Shoot From Post':60,
  'Post Hook Left':60,'Post Hook Right':60,'Post Fade Left':60,'Post Fade Right':60,
  'Post Shimmy Shot':60,'Post Hop Shot':60,'Post Step Back Shot':60,'Post Up and Under':60,
  'Takes Charge':60,'Foul':60,'Hard Foul':55,'Pass Interception':60,'On-Ball Steal':60,
  'Blocked Shot':60,'Contest Shot':60,
};

/* ── State ───────────────────────────────────────────────────────────── */
let selectedPlayer = null;
let currentResult  = null;
let searchTimer    = null;

/* ── DOM refs ────────────────────────────────────────────────────────── */
const searchInput     = document.getElementById('searchInput');
const acList          = document.getElementById('autocompleteList');
const generateBtn     = document.getElementById('generateBtn');
const debugBtn        = document.getElementById('debugBtn');
const refreshBtn      = document.getElementById('refreshBtn');
const selectedEl      = document.getElementById('selectedPlayer');
const selName         = document.getElementById('selectedName');
const selTeam         = document.getElementById('selectedTeam');
const selPos          = document.getElementById('selectedPos');
const loadingOverlay  = document.getElementById('loadingOverlay');
const loadingMsg      = document.getElementById('loadingMsg');
const resultsSection  = document.getElementById('resultsSection');
const resultName      = document.getElementById('resultName');
const resultTeam      = document.getElementById('resultTeam');
const resultPos       = document.getElementById('resultPos');
const tendencyTables  = document.getElementById('tendencyTables');
const exportCsvBtn    = document.getElementById('exportCsvBtn');
const exportExcelBtn  = document.getElementById('exportExcelBtn');
const debugSection    = document.getElementById('debugSection');
const debugContent    = document.getElementById('debugContent');
const debugCloseBtn   = document.getElementById('debugCloseBtn');
const teamSelect      = document.getElementById('teamSelect');
const bulkBtn         = document.getElementById('bulkBtn');
const bulkProgress    = document.getElementById('bulkProgress');
const progressBar     = document.getElementById('progressBar');
const progressLabel   = document.getElementById('progressLabel');
const bulkResults     = document.getElementById('bulkResults');

/* ── Init ────────────────────────────────────────────────────────────── */
NBA_TEAMS.forEach(t => {
  const opt = document.createElement('option');
  opt.value = t;
  opt.textContent = t;
  teamSelect.appendChild(opt);
});

/* ── Search ──────────────────────────────────────────────────────────── */
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 2) { hideDropdown(); return; }
  searchTimer = setTimeout(() => fetchSearch(q), 300);
});

searchInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') hideDropdown();
});

document.addEventListener('click', e => {
  if (!e.target.closest('.autocomplete-wrapper')) hideDropdown();
});

async function fetchSearch(q) {
  try {
    const res  = await fetch(`${API.search}?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    renderDropdown(Array.isArray(data) ? data : []);
  } catch {
    hideDropdown();
  }
}

function renderDropdown(items) {
  acList.innerHTML = '';
  if (!items.length) { hideDropdown(); return; }
  items.forEach(p => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="ac-name">${esc(p.name)}</span><span class="ac-team">${esc(p.team||'')}</span><span class="ac-pos">${esc(p.position||'')}</span>`;
    li.addEventListener('click', () => selectPlayer(p));
    acList.appendChild(li);
  });
  acList.classList.remove('hidden');
}

function hideDropdown() { acList.classList.add('hidden'); }

function selectPlayer(p) {
  selectedPlayer = p;
  searchInput.value = p.name;
  hideDropdown();

  selName.textContent = p.name;
  selTeam.textContent = p.team     || '';
  selPos.textContent  = p.position || '';
  selectedEl.classList.remove('hidden');
  generateBtn.disabled = false;
  debugBtn.disabled = false;
}

/* ── Generate ────────────────────────────────────────────────────────── */
generateBtn.addEventListener('click', () => {
  if (!selectedPlayer) return;
  runGenerate(selectedPlayer.player_id, selectedPlayer.name);
});

async function runGenerate(playerId, playerName) {
  showLoading('Fetching player data…');
  resultsSection.classList.add('hidden');
  try {
    const res  = await fetch(API.generate, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ player_id: playerId, player_name: playerName }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    currentResult = data;
    renderResults(data);
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    hideLoading();
  }
}

/* ── Results rendering ───────────────────────────────────────────────── */
function renderResults(data) {
  resultName.textContent = data.name || '';
  resultTeam.textContent = data.team || '';
  resultPos.textContent  = data.position || '';

  tendencyTables.innerHTML = '';
  const t = data.tendencies || {};

  for (const [catName, names] of Object.entries(CATEGORIES)) {
    const block = document.createElement('div');
    block.className = 'tend-category';

    const h3 = document.createElement('h3');
    h3.textContent = catName;
    block.appendChild(h3);

    const table = document.createElement('table');
    table.className = 'tend-table';
    table.innerHTML = `<thead><tr><th>Tendency</th><th>Cap</th><th>Value</th><th>Override</th></tr></thead>`;
    const tbody = document.createElement('tbody');

    names.forEach(name => {
      const cap = HARD_CAPS[name] || 100;
      const val = t[name] !== undefined ? t[name] : 0;
      const cls = colorClass(val, cap);

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="tend-name">${esc(name)}</td>
        <td class="tend-cap">${cap}</td>
        <td class="tend-val ${cls}">${val}</td>
        <td><input class="tend-override" type="number" min="0" max="${cap}" step="5" value="${val}" data-name="${esc(name)}" data-cap="${cap}" /></td>
      `;
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    block.appendChild(table);
    tendencyTables.appendChild(block);
  }

  // Wire override validation
  tendencyTables.querySelectorAll('.tend-override').forEach(inp => {
    inp.addEventListener('input', () => validateOverride(inp));
    inp.addEventListener('change', () => validateOverride(inp));
  });

  resultsSection.classList.remove('hidden');
}

function colorClass(val, cap) {
  const ratio = cap > 0 ? val / cap : 0;
  if (ratio >= 0.9) return 'red';
  if (ratio >= 0.7) return 'yellow';
  return 'green';
}

function validateOverride(inp) {
  let v = parseInt(inp.value, 10);
  const cap = parseInt(inp.dataset.cap, 10);
  if (isNaN(v)) { inp.classList.add('invalid'); return; }
  // Must end in 0 or 5
  if (v % 5 !== 0) {
    inp.classList.add('invalid');
    return;
  }
  v = Math.max(0, Math.min(v, cap));
  inp.value = v;
  inp.classList.remove('invalid');
  // Update displayed value cell
  const row = inp.closest('tr');
  if (row) {
    const cell = row.querySelector('.tend-val');
    cell.textContent = v;
    cell.className = 'tend-val ' + colorClass(v, cap);
  }
}

function getCurrentTendencies() {
  const t = {};
  tendencyTables.querySelectorAll('.tend-override').forEach(inp => {
    const name = inp.dataset.name;
    const v    = parseInt(inp.value, 10);
    t[name] = isNaN(v) ? 0 : v;
  });
  return t;
}

/* ── Export ──────────────────────────────────────────────────────────── */
exportCsvBtn.addEventListener('click', () => doExport('csv'));
exportExcelBtn.addEventListener('click', () => doExport('excel'));

async function doExport(type) {
  if (!currentResult) return;
  const endpoint = type === 'csv' ? API.exportCsv : API.exportExcel;
  const ext      = type === 'csv' ? 'csv' : 'xlsx';
  try {
    const res = await fetch(endpoint, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name: currentResult.name, tendencies: getCurrentTendencies() }),
    });
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${(currentResult.name || 'player').replace(/ /g,'_')}_tendencies.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert('Export error: ' + err.message);
  }
}

/* ── Refresh roster ──────────────────────────────────────────────────── */
refreshBtn.addEventListener('click', async () => {
  refreshBtn.disabled = true;
  refreshBtn.textContent = '…';
  try {
    const res  = await fetch(API.refreshRoster);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    alert(`Roster refreshed: ${data.count} players loaded.`);
  } catch (err) {
    alert('Refresh error: ' + err.message);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = '↻ Roster';
  }
});

/* ── Debug raw data ──────────────────────────────────────────────────── */
debugBtn.addEventListener('click', async () => {
  if (!selectedPlayer) return;

  showLoading('Fetching raw data…');
  try {
    const res = await fetch(API.debugRaw, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_id: selectedPlayer.player_id,
        player_name: selectedPlayer.name,
        season: '2024-25',
      }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderDebugPanel(data);
    debugSection.classList.remove('hidden');
    debugSection.scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    alert('Debug failed: ' + e.message);
  } finally {
    hideLoading();
  }
});

debugCloseBtn.addEventListener('click', () => {
  debugSection.classList.add('hidden');
});

function renderDebugPanel(data) {
  let html = `<div class="debug-header">
    <strong>${esc(data.player_name)}</strong> (ID: ${esc(String(data.player_id))}) —
    <span class="badge badge-pos">${esc(data.position)}</span>
    <span class="badge badge-team">${esc(data.team)}</span>
  </div>`;

  const sources = data.data_sources || {};
  for (const [sourceName, sourceData] of Object.entries(sources)) {
    const status = sourceData.status || 'UNKNOWN';
    const statusClass = status === 'OK' ? 'debug-ok' :
                        status === 'FAILED' ? 'debug-fail' : 'debug-warn';
    const statusEmoji = status === 'OK' ? '✅' :
                        status === 'FAILED' ? '❌' : '⚠️';

    html += `<details class="debug-source ${statusClass}">
      <summary>
        <span class="debug-status">${statusEmoji} ${esc(status)}</span>
        <strong>${esc(formatSourceName(sourceName))}</strong>
        ${sourceData.error ? `<span class="debug-error"> — ${esc(sourceData.error)}</span>` : ''}
      </summary>
      <div class="debug-data">`;

    if (sourceData.data && Object.keys(sourceData.data).length > 0) {
      html += renderDataObject(sourceData.data);
    } else {
      html += '<p class="debug-empty">No data returned</p>';
    }

    html += `</div></details>`;
  }

  debugContent.innerHTML = html;
}

function formatSourceName(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function fmtNum(v) {
  return v % 1 === 0 ? v : v.toFixed(4);
}

function renderDataObject(obj) {
  let html = '<table class="debug-table"><tbody>';

  for (const [key, value] of Object.entries(obj)) {
    let displayValue;

    if (Array.isArray(value)) {
      displayValue = '<table class="debug-subtable"><tbody>';
      for (const item of value.slice(0, 20)) {
        if (Array.isArray(item)) {
          displayValue += `<tr><td>${esc(String(item[0]))}</td><td class="debug-num">${esc(String(item[1]))}</td></tr>`;
        } else {
          displayValue += `<tr><td colspan="2">${esc(String(item))}</td></tr>`;
        }
      }
      displayValue += '</tbody></table>';
    } else if (typeof value === 'object' && value !== null) {
      displayValue = '<table class="debug-subtable"><tbody>';
      for (const [k, v] of Object.entries(value)) {
        const formatted = typeof v === 'number' ? fmtNum(v) : esc(String(v));
        displayValue += `<tr><td>${esc(k)}</td><td class="debug-num">${formatted}</td></tr>`;
      }
      displayValue += '</tbody></table>';
    } else if (value === null) {
      displayValue = '<span class="debug-null">null ⚠️</span>';
    } else if (typeof value === 'number') {
      displayValue = fmtNum(value);
    } else {
      displayValue = esc(String(value));
    }

    html += `<tr>
      <td class="debug-key">${esc(key)}</td>
      <td>${displayValue}</td>
    </tr>`;
  }

  html += '</tbody></table>';
  return html;
}

/* ── Bulk generate ───────────────────────────────────────────────────── */
bulkBtn.addEventListener('click', async () => {
  const team = teamSelect.value;
  if (!team) { alert('Please select a team.'); return; }

  bulkResults.innerHTML = '';
  bulkProgress.classList.remove('hidden');
  progressBar.style.width = '0%';
  progressLabel.textContent = '…';
  bulkBtn.disabled = true;

  try {
    const res  = await fetch(API.bulkGenerate, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ team }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const total = data.length;
    data.forEach((p, i) => {
      progressBar.style.width = `${Math.round((i + 1) / total * 100)}%`;
      progressLabel.textContent = `${i + 1} / ${total}`;

      const card = document.createElement('div');
      card.className = 'bulk-player-card';
      card.innerHTML = `<div class="bulk-player-name">${esc(p.name)}</div>
        <div class="bulk-player-meta">${esc(p.position||'')} · ${esc(p.team||'')} · ${Object.keys(p.tendencies||{}).length} tendencies</div>`;
      card.addEventListener('click', () => {
        currentResult = p;
        renderResults(p);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      bulkResults.appendChild(card);
    });

    progressBar.style.width = '100%';
    progressLabel.textContent = `${total} / ${total}`;
  } catch (err) {
    alert('Bulk error: ' + err.message);
  } finally {
    bulkBtn.disabled = false;
  }
});

/* ── Helpers ─────────────────────────────────────────────────────────── */
function showLoading(msg) {
  loadingMsg.textContent = msg || 'Loading…';
  loadingOverlay.classList.remove('hidden');
}
function hideLoading() {
  loadingOverlay.classList.add('hidden');
}
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
