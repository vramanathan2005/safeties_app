import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const SHEET_ID = '1XbxezaxViAmUPTKDaNIwc79ZUjJHG39MW6_Ttvt79_Y';
const EXTRA_RECRUITS_PATH = fs.existsSync(path.join(projectRoot, 'public', 'scouting', 'extra_recruits.json'))
  ? path.join(projectRoot, 'public', 'scouting', 'extra_recruits.json')
  : path.join(projectRoot, 'extra_recruits.json');
const INDEX_HTML_PATH = fs.existsSync(path.join(projectRoot, 'public', 'scouting', 'index.html'))
  ? path.join(projectRoot, 'public', 'scouting', 'index.html')
  : path.join(projectRoot, 'index.html');

export function parseTabDate(tab) {
  const cleaned = tab.replace(/\\\//g, '/').trim();
  let target = cleaned;
  if (target.includes('-')) {
    const parts = target.split('-').map(s => s.trim());
    const datePart = parts[parts.length - 1];
    if (/\d/.test(datePart)) target = datePart;
  }
  
  // Format: M/D/YY or M.D.YY or MM/DD/YYYY
  let m = target.match(/(\d{1,2})[\/\.](\d{1,2})[\/\.](\d{2,4})/);
  if (m) {
    let [_, mo, d, y] = m;
    let year = y.length === 2 ? (Number(y) >= 90 ? '19' + y : '20' + y) : y;
    let month = mo.padStart(2, '0');
    let day = d.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  // Format: M/D without year (e.g. UOV 3/13, UOV 3/5 in 2026 master sheet)
  m = target.match(/(\d{1,2})\/(\d{1,2})/);
  if (m) {
    let [_, mo, d] = m;
    let month = mo.padStart(2, '0');
    let day = d.padStart(2, '0');
    return `2026-${month}-${day}`;
  }
  
  return null;
}

export function parseHeight(raw) {
  if (!raw) return null;
  const str = String(raw).trim();
  if (!str || str === '-' || str === 'NA' || str === 'N/A' || str === 'null') return null;

  if (/^\d{2}(\.\d+)?$/.test(str)) {
    const v = parseFloat(str);
    if (v >= 55 && v <= 85) return Math.round(v * 100) / 100;
  }

  const clean = str.replace(/[^0-9]/g, '');
  if (clean.length === 4) {
    const feet = parseInt(clean[0], 10);
    const inches = parseInt(clean.slice(1, 3), 10);
    const eighths = parseInt(clean[3], 10);
    if (feet >= 5 && feet <= 7 && inches < 12 && eighths <= 8) {
      return Math.round((feet * 12 + inches + eighths / 8) * 100) / 100;
    }
  }
  return null;
}

export function parseScoutMeasurement(raw, minVal = 0, maxVal = 100) {
  if (!raw) return null;
  let str = String(raw).trim().toUpperCase();
  if (!str || str === '-' || str === 'NA' || str === 'N/A' || str === 'null') return null;

  // Strip trailing L or R
  str = str.replace(/[LR]$/, '');

  if (/^\d{1,2}(\.\d+)?$/.test(str)) {
    const v = parseFloat(str);
    if (v >= minVal && v <= maxVal) return Math.round(v * 100) / 100;
  }

  let clean = str.replace(/[^0-9]/g, '');
  if (clean.length === 3) {
    clean = clean.padStart(4, '0');
  }

  if (clean.length === 4) {
    // Check for 8000 / 9000
    if ((clean === '8000' || clean === '9000' || clean === '7000') && maxVal <= 14) {
      const v = parseInt(clean[0], 10);
      if (v >= minVal && v <= maxVal) return v;
    }

    const inches = parseInt(clean.slice(0, 2), 10);
    const eighthsPart = clean.slice(2);
    const eighths = eighthsPart === '00' ? 0 : parseInt(clean[2], 10);
    const val = Math.round((inches + eighths / 8) * 100) / 100;
    if (val >= minVal && val <= maxVal) return val;
  }
  return null;
}

export function parseWeight(raw) {
  if (!raw) return null;
  const clean = String(raw).replace(/[^0-9.]/g, '');
  const v = parseFloat(clean);
  if (!isNaN(v) && v >= 100 && v <= 450) return Math.round(v);
  return null;
}

export function mapPosition(rawPos) {
  if (!rawPos) return 'wr';
  const p = rawPos.trim().toUpperCase();
  if (p === 'QB') return 'qb';
  if (p === 'RB' || p === 'WR/RB') return 'rb';
  if (p === 'WR') return 'wr';
  if (p === 'TE' || p.startsWith('TE/')) return 'te';
  if (p === 'OL' || p === 'OG' || p === 'OT' || p === 'C') return 'ol';
  if (p === 'SAF' || p === 'FS' || p === 'SS' || p === 'DB') return 'safety';
  if (p === 'CB') return 'cb';
  if (p === 'LB' || p === 'ILB' || p === 'OLB') return 'lb';
  if (p === 'EDGE' || p === 'DE' || p === 'LB/EDGE') return 'de';
  if (p === 'DL' || p === 'DT' || p === 'NT') return 'dt';
  return 'wr';
}

export function getCompatiblePositionGroups(rawPos) {
  if (!rawPos) return ['qb', 'rb', 'wr', 'te', 'ol', 'safety', 'cb', 'lb', 'de', 'dt'];
  const p = rawPos.trim().toUpperCase();
  if (p === 'QB') return ['qb'];
  if (p === 'RB' || p === 'FB') return ['rb'];
  if (p === 'WR') return ['wr'];
  if (p === 'WR/RB') return ['wr', 'rb'];
  if (p === 'TE') return ['te'];
  if (p.startsWith('TE/')) return ['te', 'wr', 'de', 'dt'];
  if (p === 'OL' || p === 'OG' || p === 'OT' || p === 'C') return ['ol'];
  if (p === 'SAF' || p === 'FS' || p === 'SS') return ['safety', 'cb'];
  if (p === 'CB') return ['cb', 'safety'];
  if (p === 'DB') return ['safety', 'cb'];
  if (p === 'LB' || p === 'ILB' || p === 'OLB') return ['lb', 'de'];
  if (p === 'LB/EDGE') return ['lb', 'de'];
  if (p === 'EDGE' || p === 'DE') return ['de', 'dt', 'lb'];
  if (p === 'DL' || p === 'DT' || p === 'NT') return ['dt', 'de'];
  return ['wr', 'rb', 'safety', 'cb', 'te', 'qb', 'lb', 'de', 'dt', 'ol'];
}

export function schoolsMatch(sheetSchool, playerSchool) {
  if (!sheetSchool || !playerSchool) return true;
  const stopWords = new Set(['high', 'school', 'senior', 'middle', 'hs', 'prep', 'academy', 'the', 'of', 'and', 'at']);
  const cleanWords = (s) => String(s).toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w.length > 2 && !stopWords.has(w));
  const w1 = cleanWords(sheetSchool);
  const w2 = cleanWords(playerSchool);
  if (!w1.length || !w2.length) return true;
  return w1.some(w => w2.includes(w));
}

function parseCsvLine(line) {
  const cols = [];
  let inQuote = false;
  let cur = '';
  for (const ch of line) {
    if (ch === '"') {
      inQuote = !inQuote;
    } else if (ch === ',' && !inQuote) {
      cols.push(cur.trim());
      cur = '';
    } else {
      cur += ch;
    }
  }
  cols.push(cur.trim());
  return cols.map(s => s.replace(/^"|"$/g, '').trim());
}

async function syncMeasurables() {
  console.log(`Fetching Google Sheet HTML view from sheet ${SHEET_ID}...`);
  const htmlRes = await fetch(`https://docs.google.com/spreadsheets/d/${SHEET_ID}/htmlview`);
  if (!htmlRes.ok) {
    throw new Error(`Failed to fetch sheet htmlview: ${htmlRes.statusText}`);
  }
  const html = await htmlRes.text();

  const tabRegex = /items\.push\({\s*name:\s*"([^"]+)",\s*pageUrl:\s*"[^"]*",\s*gid:\s*"([^"]+)"/g;
  const rawTabs = [];
  let m;
  while ((m = tabRegex.exec(html)) !== null) {
    const name = m[1].replace(/\\\//g, '/');
    if (name !== 'Template') {
      rawTabs.push({ name, gid: m[2], date: parseTabDate(name) });
    }
  }

  console.log(`Found ${rawTabs.length} event tabs.`);
  // Sort chronologically ascending so newer events supersede older events
  rawTabs.sort((a, b) => {
    if (!a.date) return -1;
    if (!b.date) return 1;
    return a.date.localeCompare(b.date);
  });

  // Map of normalized name -> aggregate prospect
  const prospects = new Map();

  for (const tab of rawTabs) {
    const csvUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&gid=${tab.gid}`;
    const csvRes = await fetch(csvUrl);
    if (!csvRes.ok) {
      console.warn(`Warning: failed to fetch tab ${tab.name} (${csvUrl})`);
      continue;
    }
    const csv = await csvRes.text();
    const lines = csv.split('\n').map(l => l.replace(/\r$/, ''));
    if (lines.length <= 1) continue;

    const header = parseCsvLine(lines[0]).map(s => s.toUpperCase());
    const firstIdx = header.indexOf('FIRST');
    const lastIdx = header.indexOf('LAST');
    const yearIdx = header.indexOf('YEAR');
    const posIdx = header.indexOf('POS');
    const schoolIdx = header.indexOf('SCHOOL');
    const stIdx = header.indexOf('ST');
    const htIdx = header.indexOf('HT');
    const wtIdx = header.indexOf('WT');
    const armIdx = header.indexOf('ARM');
    const wingIdx = header.indexOf('WING');
    const handIdx = header.indexOf('HAND');

    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      const clean = parseCsvLine(lines[i]);
      const first = clean[firstIdx];
      const last = clean[lastIdx];
      if (!first || !last) continue;

      const normName = `${first} ${last}`.toLowerCase().trim();
      const ht = parseHeight(clean[htIdx]);
      const wt = parseWeight(clean[wtIdx]);
      const arm = parseScoutMeasurement(clean[armIdx], 25, 45);
      const wing = parseScoutMeasurement(clean[wingIdx], 60, 95);
      const hand = parseScoutMeasurement(clean[handIdx], 6, 14);

      const rawYear = clean[yearIdx];
      const classYear = rawYear && /^\d{4}$/.test(rawYear) ? parseInt(rawYear, 10) : 2026;
      const rawPos = clean[posIdx];
      const school = clean[schoolIdx] || '';
      const state = clean[stIdx] || '';

      const existing = prospects.get(normName);
      if (!existing) {
        prospects.set(normName, {
          first,
          last,
          name: `${first} ${last}`,
          normName,
          classYear,
          rawPos,
          posCode: mapPosition(rawPos),
          school: school + (state ? `, ${state}` : ''),
          ht,
          wt,
          arm,
          wing,
          hand,
          measurement_date: tab.date,
          measurement_source: `Texas In-Person (${tab.name})`
        });
      } else {
        // Only update if newer or equal date
        if (!existing.measurement_date || (tab.date && tab.date >= existing.measurement_date)) {
          if (ht !== null) existing.ht = ht;
          if (wt !== null) existing.wt = wt;
          if (arm !== null) existing.arm = arm;
          if (wing !== null) existing.wing = wing;
          if (hand !== null) existing.hand = hand;
          if (tab.date) {
            existing.measurement_date = tab.date;
            existing.measurement_source = `Texas In-Person (${tab.name})`;
          }
          if (rawPos && !existing.rawPos) {
            existing.rawPos = rawPos;
            existing.posCode = mapPosition(rawPos);
          }
          if (school && !existing.school) {
            existing.school = school + (state ? `, ${state}` : '');
          }
        }
      }
    }
  }

  console.log(`Parsed ${prospects.size} unique prospects from all Google Sheet tabs.`);

  // Load extra_recruits.json
  console.log(`Loading ${EXTRA_RECRUITS_PATH}...`);
  const extraRecruits = JSON.parse(fs.readFileSync(EXTRA_RECRUITS_PATH, 'utf8'));

  // Load index.html
  console.log(`Loading ${INDEX_HTML_PATH}...`);
  const indexHtml = fs.readFileSync(INDEX_HTML_PATH, 'utf8');
  const startMarker = 'const posData = ';
  const startIdx = indexHtml.indexOf(startMarker);
  const endMarker = ';\n        const DEFAULT_YEARS = [2027,2028];';
  const endIdx = indexHtml.indexOf(endMarker, startIdx);

  if (startIdx === -1 || endIdx === -1) {
    throw new Error('Could not find posData delimiters in index.html');
  }

  const posDataJsonStr = indexHtml.slice(startIdx + startMarker.length, endIdx);
  const posData = JSON.parse(posDataJsonStr);

  let updatedInPosData = 0;
  let updatedInExtra = 0;
  let addedNewRecruits = 0;

  // Pre-index existing players by normalized name
  const existingByName = new Map();
  for (const posCode of Object.keys(posData)) {
    if (!posData[posCode]?.players) continue;
    for (const pl of posData[posCode].players) {
      if (!pl.NAME) continue;
      const n = pl.NAME.toLowerCase().trim();
      if (!existingByName.has(n)) existingByName.set(n, []);
      existingByName.get(n).push({ source: 'posData', posCode, player: pl });
    }
  }
  for (const posCode of Object.keys(extraRecruits)) {
    if (!extraRecruits[posCode]?.players) continue;
    for (const pl of extraRecruits[posCode].players) {
      if (!pl.NAME) continue;
      const n = pl.NAME.toLowerCase().trim();
      if (!existingByName.has(n)) existingByName.set(n, []);
      existingByName.get(n).push({ source: 'extra', posCode, player: pl });
    }
  }

  for (const [normName, p] of prospects) {
    const candidates = existingByName.get(normName) || [];
    const compatibleGroups = getCompatiblePositionGroups(p.rawPos);

    // 1. Filter candidates by position compatibility
    let matchingCandidates = candidates.filter(c => compatibleGroups.includes(c.posCode));

    // 2. If multiple candidates share the name, disambiguate by school/state
    if (matchingCandidates.length > 1) {
      const bySchool = matchingCandidates.filter(c => schoolsMatch(p.school, c.player.SCHOOL));
      if (bySchool.length > 0) {
        matchingCandidates = bySchool;
      }
    } else if (matchingCandidates.length === 1 && candidates.length > 1) {
      // Exactly 1 candidate had a compatible position while others had incompatible positions
      // Ensure the candidate's school does not completely contradict if both schools are known
      if (!schoolsMatch(p.school, matchingCandidates[0].player.SCHOOL)) {
        matchingCandidates = [];
      }
    }

    let matchedInPosData = false;
    let matchedInExtra = false;

    for (const c of matchingCandidates) {
      const pl = c.player;
      if (c.source === 'posData') matchedInPosData = true;
      if (c.source === 'extra') matchedInExtra = true;

      const isNewer = !pl.measurement_date || (p.measurement_date && p.measurement_date >= pl.measurement_date);
      if (isNewer) {
        if (p.ht !== null) pl.HT = p.ht;
        if (p.wt !== null) pl.WT = p.wt;
        if (p.arm !== null) pl.ARM = p.arm;
        if (p.wing !== null) pl.WING = p.wing;
        if (p.hand !== null) pl.HAND = p.hand;
        pl.measurement_date = p.measurement_date;
        pl.measurement_source = p.measurement_source;
        if (c.source === 'posData') updatedInPosData++;
        if (c.source === 'extra') updatedInExtra++;
      }
    }

    // 3. If not found in either, add as a new recruit
    if (!matchedInPosData && !matchedInExtra) {
      const targetPosCode = p.posCode || 'wr';
      const newPlayerRecord = {
        NAME: p.name,
        SCHOOL: p.school || 'High School Recruit',
        TEAM: 'High School Recruit',
        YEAR: null,
        ROUND: null,
        'PICK #': null,
        HT: p.ht,
        WT: p.wt,
        ARM: p.arm,
        WING: p.wing,
        HAND: p.hand,
        '40': null,
        SHUT: null,
        VERT: null,
        BROAD: null,
        '100M': null,
        '110HH': null,
        '200M': null,
        '300IH': null,
        '400M': null,
        HJ: null,
        LJ: null,
        TJ: null,
        SHOT: null,
        is_recruit: true,
        class_field: p.classYear,
        career_outcome: 'High School Recruit',
        measurement_date: p.measurement_date,
        measurement_source: p.measurement_source
      };

      // Add to extra_recruits.json
      if (extraRecruits[targetPosCode]) {
        extraRecruits[targetPosCode].players.push(newPlayerRecord);
      }

      // If class is 2027 or 2028 (the default view classes in posData), also add to posData
      if ((p.classYear === 2027 || p.classYear === 2028) && posData[targetPosCode]) {
        posData[targetPosCode].players.push(newPlayerRecord);
      }

      addedNewRecruits++;
    }
  }

  console.log(`Sync Summary:`);
  console.log(`- Updated in posData (index.html): ${updatedInPosData} player entries`);
  console.log(`- Updated in extra_recruits.json: ${updatedInExtra} player entries`);
  console.log(`- Added new recruits: ${addedNewRecruits}`);

  function stripNulls(obj) {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (v !== null && v !== undefined) out[k] = v;
    }
    return out;
  }

  // Write updated extra_recruits.json (compact minified with null values omitted to fit GitHub & Cloudflare limits)
  console.log(`Writing compact ${EXTRA_RECRUITS_PATH}...`);
  const compactExtra = {};
  for (const [pos, group] of Object.entries(extraRecruits)) {
    compactExtra[pos] = {
      name: group.name,
      players: group.players.map(stripNulls)
    };
  }
  fs.writeFileSync(EXTRA_RECRUITS_PATH, JSON.stringify(compactExtra), 'utf8');

  // Write updated index.html with compact posData and card template updates
  console.log(`Updating HTML and writing compact ${INDEX_HTML_PATH}...`);
  const compactPosData = {};
  for (const [pos, group] of Object.entries(posData)) {
    compactPosData[pos] = {
      name: group.name,
      players: (group.players || []).map(stripNulls)
    };
  }
  let updatedHtml = indexHtml.slice(0, startIdx + startMarker.length) +
    JSON.stringify(compactPosData) +
    indexHtml.slice(endIdx);

  // Update card header if not already updated
  if (!updatedHtml.includes('card-verified')) {
    const cardTarget = '<div class="card-school">${escapeText(p.SCHOOL || \'-\')} • ${escapeText(draftInfo)}</div>\n                    </div>';
    const cardReplacement = '<div class="card-school">${escapeText(p.SCHOOL || \'-\')} • ${escapeText(draftInfo)}</div>\n' +
      '                        ${p.measurement_date ? `<div class="card-verified" style="font-size:0.75rem;color:#bf5700;font-weight:600;margin-top:3px;display:flex;align-items:center;gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg> Measured: ${escapeText(p.measurement_date)}${escapeText(p.measurement_source ? " · " + p.measurement_source : "")}</div>` : \'\'}\n' +
      '                    </div>';
    if (updatedHtml.includes(cardTarget)) {
      updatedHtml = updatedHtml.replace(cardTarget, cardReplacement);
      console.log('Added verified measurement date badge to player cards.');
    }
  }

  // Update hover tooltips if not already updated
  const histTooltipTarget = "document.getElementById('ht-school').textContent = recruit.SCHOOL || '-';";
  const histTooltipReplacement = "document.getElementById('ht-school').textContent = (recruit.SCHOOL || '-') + (recruit.measurement_date ? ` • Measured: ${recruit.measurement_date}` : '');";
  if (updatedHtml.includes(histTooltipTarget)) {
    updatedHtml = updatedHtml.replace(histTooltipTarget, histTooltipReplacement);
    console.log('Updated histogram hover tooltip with measurement date.');
  }

  const scatterTextTarget = "text: valid.map(p => p.NAME),";
  const scatterTextReplacement = "text: valid.map(p => p.NAME + (p.measurement_date ? ` (Measured: ${p.measurement_date})` : '')),";
  if (updatedHtml.includes(scatterTextTarget)) {
    updatedHtml = updatedHtml.replace(scatterTextTarget, scatterTextReplacement);
    console.log('Updated scatter plot hover labels with measurement date.');
  }

  fs.writeFileSync(INDEX_HTML_PATH, updatedHtml, 'utf8');

  console.log('Sync complete!');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  syncMeasurables().catch(err => {
    console.error('Sync failed:', err);
    process.exit(1);
  });
}
