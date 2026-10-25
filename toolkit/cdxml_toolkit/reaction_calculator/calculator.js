// The calculator page: a table whose fixed quantity on each row drives the others (engine.js).
// Everything works offline; the buttons that need the local server (drawing in ChemDraw,
// looking up names and SMILES) appear only when the page was opened by `cdx.py calc`.
(function () {
  'use strict';
  var E = window.CalcEngine;
  var payload = JSON.parse(document.getElementById('payload').textContent);
  var S = payload.state, LIB = payload.library || [], API = payload.api || null;
  var result = null, history = [], seq = 1000, statusTimer = null;
  var AMOUNT = ['reactant', 'reagent', 'catalyst'];
  var $ = function (id) { return document.getElementById(id); };

  function el(tag, props, kids) {
    var node = document.createElement(tag), k;
    Object.keys(props || {}).forEach(function (key) {
      if (key === 'text') node.textContent = props[key];
      else if (key === 'html') node.innerHTML = props[key];
      else if (key === 'class') node.className = props[key];
      else node.setAttribute(key, props[key]);
    });
    (kids || []).forEach(function (kid) { if (kid) node.appendChild(kid); });
    return node;
  }

  // ---- numbers ----------------------------------------------------------------------
  function fmt(x) {
    if (x === null || x === undefined || !isFinite(x)) return '';
    if (x === 0) return '0';
    var s = String(Number(x.toPrecision(4)));
    return s.indexOf('e') >= 0 ? x.toPrecision(4) : s;
  }
  function sig(x, digits) {
    if (x === null || x === undefined || !isFinite(x)) return '';
    var s = String(Number(x.toPrecision(digits || 3)));
    return s.indexOf('e') >= 0 ? x.toPrecision(digits || 3) : s;
  }
  function volumeText(ml) { return ml < 0.1 ? sig(ml * 1000, 3) + ' µL' : sig(ml, 3) + ' mL'; }
  function amountText(r) {
    var parts = [], liquid = r.volume_ml !== null && r.volume_ml !== undefined;
    if (liquid && r.solution_m) parts.push(volumeText(r.volume_ml) + ' of ' + sig(r.solution_m, 3) + ' M solution');
    else if (liquid) parts.push(volumeText(r.volume_ml));
    else parts.push(sig(r.mass_mg, 3) + ' mg');
    parts.push(sig(r.mmol, 3) + ' mmol');
    parts.push(sig(r.equiv, 3) + ' equiv');
    return '(' + parts.join(', ') + ')';
  }

  // ---- state helpers ----------------------------------------------------------------
  function find(id) { return S.rows.filter(function (r) { return r.id === id; })[0]; }
  function computed(id) { return result && result.rows.filter(function (r) { return r.id === id; })[0]; }
  function snapshot() { history.push(JSON.stringify(S)); if (history.length > 200) history.shift(); }
  function say(message, kind, keep) {
    var node = $('status');
    node.textContent = message || '';
    node.className = kind || '';
    clearTimeout(statusTimer);
    if (message && !keep && kind !== 'err') statusTimer = setTimeout(function () { node.textContent = ''; node.className = ''; }, 7000);
  }
  function tryCompute(state) {
    try { return { value: E.compute(state) }; } catch (e) { return { error: e.message }; }
  }
  function apply(mutate, okMessage) {
    var before = JSON.stringify(S), attempt;
    try { mutate(); attempt = tryCompute(S); } catch (e) { attempt = { error: e.message }; }
    if (attempt.error) {
      S = JSON.parse(before);
      say(attempt.error, 'err');
      refresh();
      return false;
    }
    history.push(before);
    if (history.length > 200) history.shift();
    result = attempt.value;
    if (okMessage) say(okMessage, 'ok');
    return true;
  }

  // ---- rendering --------------------------------------------------------------------
  var inputs = {};
  function numInput(id, field, extra) {
    var input = el('input', { 'class': 'num ' + (extra || ''), type: 'text', inputmode: 'decimal', autocomplete: 'off', spellcheck: 'false', 'data-id': id, 'data-field': field });
    inputs[id + '|' + field] = input;
    if (/ro/.test(extra || '')) { input.readOnly = true; input.tabIndex = -1; return input; }
    input.addEventListener('change', function () { commit(id, field, input.value); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') input.blur(); });
    return input;
  }
  function cell(content, cls) { var td = el('td', { 'class': cls || '' }); if (content) td.appendChild(content); return td; }

  function reagentRow(r) {
    var tr = el('tr', { 'data-row': r.id });
    var radio = el('input', { type: 'radio', name: 'limiting', 'aria-label': 'Limiting reagent: ' + r.name });
    if (AMOUNT.indexOf(r.role) < 0) radio.disabled = true;
    radio.checked = S.limiting === r.id;
    radio.addEventListener('change', function () {
      apply(function () { S = E.rebase(S, r.id); }, r.name + ' is now the limiting reagent; every amount is unchanged.');
      build();
    });
    tr.appendChild(cell(radio, 'l'));
    tr.appendChild(el('td', { 'class': 'thumb', html: r.svg || '' }));
    var name = el('input', { 'class': 'txt', type: 'text', value: r.name, 'aria-label': 'Name' });
    name.addEventListener('change', function () { apply(function () { find(r.id).name = name.value.trim() || r.formula; }); build(); });
    tr.appendChild(cell(name, 'l'));
    var mw = numInput(r.id, 'mw', 'narrow');
    tr.appendChild(cell(mw));
    if (r.role === 'solvent') {
      var td = el('td', { 'class': 'solv', colspan: '3' });
      td.appendChild(numInput(r.id, 'conc', 'narrow'));
      td.appendChild(el('span', { 'class': 'suffix', text: 'M of the limiting reagent' }));
      tr.appendChild(td);
      tr.appendChild(cell(numInput(r.id, 'volume')));
    } else {
      ['equiv', 'mmol', 'mass', 'volume'].forEach(function (f) { tr.appendChild(cell(numInput(r.id, f))); });
    }
    tr.appendChild(cell(numInput(r.id, 'density', 'narrow')));
    tr.appendChild(cell(r.role === 'solvent' ? null : numInput(r.id, 'solution_m', 'narrow')));
    tr.appendChild(cell(r.role === 'solvent' ? null : numInput(r.id, 'purity', 'narrow')));
    tr.appendChild(cell(removeButton(r), 'l'));
    return tr;
  }
  function removeButton(r) {
    var b = el('button', { 'class': 'x', type: 'button', title: 'Remove', 'aria-label': 'Remove ' + r.name, text: '×' });
    b.addEventListener('click', function () {
      if (r.id === S.limiting) { say('Choose another limiting reagent before removing this one.', 'err'); return; }
      apply(function () { S.rows = S.rows.filter(function (x) { return x.id !== r.id; }); });
      build();
    });
    return b;
  }
  function productRow(r) {
    var tr = el('tr', { 'data-row': r.id });
    tr.appendChild(el('td', { 'class': 'thumb', html: r.svg || '' }));
    var name = el('input', { 'class': 'txt', type: 'text', value: r.name, 'aria-label': 'Name' });
    name.addEventListener('change', function () { apply(function () { find(r.id).name = name.value.trim() || r.formula; }); build(); });
    tr.appendChild(cell(name, 'l'));
    tr.appendChild(cell(numInput(r.id, 'mw', 'narrow')));
    tr.appendChild(cell(numInput(r.id, 'coefficient', 'narrow')));
    tr.appendChild(cell(numInput(r.id, 'theory_mmol', 'ro')));
    tr.appendChild(cell(numInput(r.id, 'theory_mg', 'ro')));
    tr.appendChild(cell(numInput(r.id, 'actual')));
    tr.appendChild(cell(numInput(r.id, 'yield')));
    tr.appendChild(cell(removeButton(r), 'l'));
    return tr;
  }
  function hrmsRow(r) {
    var line = el('button', { 'class': 'hrms', type: 'button', title: 'Copy the HRMS line', text: r.hrms });
    line.addEventListener('click', function () { copy(r.hrms + '.', 'the HRMS line'); });
    return el('tr', { 'class': 'hrms-row' }, [el('td'), el('td', { colspan: '8', 'class': 'l' }, [line])]);
  }
  function group(title, colspan) { return el('tr', { 'class': 'group' }, [el('td', { colspan: String(colspan), text: title })]); }

  function build() {
    inputs = {};
    var body = $('rows'), prods = $('products');
    body.textContent = '';
    prods.textContent = '';
    [['reactant', 'Reactants'], ['reagent', 'Reagents'], ['catalyst', 'Catalysts'], ['solvent', 'Solvent']].forEach(function (g) {
      var members = S.rows.filter(function (r) { return r.role === g[0]; });
      if (!members.length) return;
      body.appendChild(group(g[1], 12));
      members.forEach(function (r) { body.appendChild(reagentRow(r)); });
    });
    var made = S.rows.filter(function (r) { return r.role === 'product'; });
    made.forEach(function (r) { prods.appendChild(productRow(r)); if (r.hrms) prods.appendChild(hrmsRow(r)); });
    $('products-card').hidden = !made.length;
    $('title').textContent = S.title || 'Reaction';
    renderScheme();
    if (!S.rows.length) {
      result = null;
      say('Nothing here yet. Add a reactant below, or press Draw in ChemDraw.');
    } else {
      var attempt = tryCompute(S);
      result = attempt.value || result;
      if (attempt.error) say(attempt.error, 'err');
    }
    refresh();
  }

  function renderScheme() {
    var box = $('scheme');
    box.textContent = '';
    function species(r) { return el('div', { 'class': 'sp' }, [el('div', { html: r.svg || '' }), el('span', { text: r.name })]); }
    function join(rows) {
      rows.forEach(function (r, i) {
        if (i) box.appendChild(el('div', { 'class': 'op', text: '+' }));
        box.appendChild(species(r));
      });
    }
    var left = S.rows.filter(function (r) { return r.role === 'reactant'; });
    var right = S.rows.filter(function (r) { return r.role === 'product'; });
    var agents = S.rows.filter(function (r) { return r.role === 'reagent' || r.role === 'catalyst' || r.role === 'solvent'; });
    if (!left.length && !right.length) { box.appendChild(el('p', { 'class': 'empty', text: 'No reaction yet. Add species below, or draw in ChemDraw.' })); return; }
    join(left);
    var arrow = el('div', { 'class': 'arrow' }, [el('span', { text: agents.filter(function (a) { return a.role !== 'solvent'; }).map(function (a) { return a.name; }).join(', ') }), el('b'), el('span', { text: agents.filter(function (a) { return a.role === 'solvent'; }).map(function (a) { return a.name; }).join(', ') })]);
    box.appendChild(arrow);
    join(right);
  }

  var FIELD_BASIS = { equiv: 'equiv', mmol: 'mmol', mass: 'mass', volume: 'volume', conc: 'conc', actual: 'mass', yield: 'yield' };
  function refresh() {
    if (!result) {
      $('stats').textContent = '';
      $('procedure').textContent = '';
      $('warnings').textContent = '';
      $('undo').disabled = !history.length;
      return;
    }
    var active = document.activeElement;
    S.rows.forEach(function (r) {
      var c = computed(r.id);
      if (!c) return;
      var shown = {
        mw: r.mw, equiv: c.equiv, mmol: c.mmol, mass: c.mass_mg, volume: c.volume_ml,
        density: r.density, solution_m: r.solution_m, purity: r.purity === 1 ? null : r.purity * 100,
        conc: r.basis === 'conc' ? r.value : (result.totals.concentration_m || null),
        coefficient: r.coefficient, theory_mmol: c.theory_mmol, theory_mg: c.theory_mg,
        actual: c.actual_mg, yield: c.yield_percent
      };
      if (r.role === 'solvent') shown.volume = c.volume_ml;
      Object.keys(shown).forEach(function (field) {
        var input = inputs[r.id + '|' + field];
        if (!input) return;
        if (input !== active) input.value = fmt(shown[field]);
        var isFixed = FIELD_BASIS[field] === r.basis && (r.role === 'product' ? (field === 'actual' || field === 'yield') : true);
        input.classList.toggle('fixed', !!isFixed);
        input.classList.toggle('assumed', !!(isFixed && r.assumed));
      });
      var eq = inputs[r.id + '|equiv'];
      if (eq) eq.disabled = r.id === S.limiting;
      var mol = inputs[r.id + '|mw'];
      if (mol) mol.classList.toggle('assumed', false);
    });
    var t = result.totals, main = result.rows.filter(function (r) { return r.role === 'product'; })[0];
    var limiting = computed(S.limiting);
    var stats = [
      ['Scale', fmt(t.limiting_mmol) + ' mmol', limiting ? limiting.name + ', ' + fmt(limiting.mass_mg) + ' mg' : '', ''],
      ['Concentration', t.concentration_m ? fmt(t.concentration_m) + ' M' : '—', t.solvent_ml ? fmt(t.solvent_ml) + ' mL solvent' : 'no solvent set', ''],
      ['Mass in', fmt(t.input_mg) + ' mg', 'reactants, reagents, catalysts', ''],
      ['Atom economy', t.atom_economy_percent === undefined ? '—' : fmt(t.atom_economy_percent) + ' %', 'first product over reactants', ''],
      ['Theoretical yield', main ? fmt(main.theory_mg) + ' mg' : '—', main ? main.name : '', ''],
      ['Yield', main && main.yield_percent !== null ? fmt(main.yield_percent) + ' %' : '—', main && main.actual_mg !== null ? fmt(main.actual_mg) + ' mg isolated' : 'enter isolated mass', main && main.yield_percent !== null ? 'good' : '']
    ];
    var box = $('stats');
    box.textContent = '';
    stats.forEach(function (s) { box.appendChild(el('div', { 'class': 'stat ' + s[3] }, [el('span', { text: s[0] }), el('b', { text: s[1] }), el('span', { text: s[2] })])); });
    var warnings = $('warnings');
    warnings.textContent = result.warnings.join(' ');
    $('procedure').textContent = procedure();
    $('undo').disabled = !history.length;
  }

  // ---- edits ------------------------------------------------------------------------
  function commit(id, field, text) {
    var row = find(id), raw = String(text).trim().replace(',', '.');
    var value = raw === '' ? null : Number(raw);
    if (value !== null && (!isFinite(value) || value < 0)) { say('Enter a non-negative number.', 'err'); refresh(); return; }
    apply(function () {
      var r = find(id);
      switch (field) {
        case 'equiv': case 'mmol': case 'mass': case 'volume':
          if (value === null) throw new Error('Enter a number, or leave the field unchanged.');
          r.basis = FIELD_BASIS[field]; r.value = value; r.assumed = false; break;
        case 'conc':
          if (!value) throw new Error('Enter a molarity above zero.');
          r.basis = 'conc'; r.value = value; r.assumed = false; break;
        case 'mw': if (!value) throw new Error('Molecular weight must be above zero.'); r.mw = value; break;
        case 'density': r.density = value || null; break;
        case 'solution_m': r.solution_m = value || null; break;
        case 'purity': r.purity = value === null || value === 0 ? 1 : Math.min(value, 100) / 100; break;
        case 'coefficient': if (!value) throw new Error('Coefficient must be above zero.'); r.coefficient = value; break;
        case 'actual':
          if (value === null) { r.basis = null; r.value = null; } else { r.basis = 'mass'; r.value = value; } break;
        case 'yield':
          if (value === null) { r.basis = null; r.value = null; } else { r.basis = 'yield'; r.value = value; } break;
      }
    });
    refresh();
  }
  function undo() {
    if (!history.length) return;
    S = JSON.parse(history.pop());
    build();
    say('Undone.', 'ok');
  }

  // ---- adding species ----------------------------------------------------------------
  function libraryFind(text) {
    var key = text.trim().toLowerCase();
    for (var i = 0; i < LIB.length; i++) {
      var e = LIB[i];
      if (e.name.toLowerCase() === key || (e.aliases || []).some(function (a) { return a.toLowerCase() === key; })) return e;
    }
    return null;
  }
  function addRow(spec) {
    var role = $('add-role').value, id = 'u' + (seq++);
    var first = !S.limiting && AMOUNT.indexOf(role) >= 0;
    if (!S.limiting && !first) { say('Add the limiting reactant first.', 'err'); return; }
    var row = { id: id, role: role, name: spec.name, formula: spec.formula || '', smiles: spec.smiles || '', mw: spec.mw, coefficient: 1, svg: spec.svg || null, density: spec.density || null, solution_m: null, purity: 1, assumed: true };
    if (role === 'solvent') { row.basis = 'volume'; row.value = 0; }
    else if (role === 'product') { row.basis = null; row.value = null; row.assumed = false; }
    else if (role === 'catalyst') { row.basis = 'equiv'; row.value = 0.05; }
    else if (role === 'reactant') { row.basis = 'equiv'; row.value = 1; }
    else { row.basis = 'equiv'; row.value = 1; }
    if (first) { row.basis = 'mmol'; row.value = 1; }
    var message = first ? 'Added ' + row.name + ' as the limiting reagent at 1 mmol; type its real amount.' : 'Added ' + row.name + '. Its amount is a default; type over it.';
    if (apply(function () { S.rows.push(row); if (first) S.limiting = row.id; }, message)) build();
  }
  function addFromInput() {
    var text = $('add-name').value.trim();
    if (!text) { say('Type a name, abbreviation or formula first.', 'err'); return; }
    var typedMw = Number($('add-mw').value), typedDensity = Number($('add-density').value) || null;
    var known = libraryFind(text);
    if (known && !(typedMw > 0)) { addRow({ name: known.name, formula: known.formula, smiles: known.smiles, mw: known.mw, density: typedDensity || known.density, svg: known.svg }); clearAdd(); return; }
    function finish(spec) { addRow(spec); clearAdd(); }
    if (typedMw > 0) { finish({ name: text, mw: typedMw, density: typedDensity }); return; }
    function viaFormula() {
      var mw = E.formulaWeight(text);
      if (mw) finish({ name: text, formula: text, mw: Math.round(mw * 1000) / 1000, density: typedDensity });
      else { say('Could not work out a molecular weight for "' + text + '". Type the MW in the field next to it.', 'err'); $('add-mw').focus(); }
    }
    if (!API) { viaFormula(); return; }
    say('Looking up ' + text + '…', '', true);
    post('/api/resolve', { query: text }).then(function (r) {
      if (r.ok) finish({ name: r.name || text, formula: r.formula, smiles: r.smiles, mw: r.mw, density: typedDensity || r.density, svg: r.svg });
      else viaFormula();
    }).catch(function () { viaFormula(); });
  }
  function clearAdd() { $('add-name').value = ''; $('add-mw').value = ''; $('add-density').value = ''; $('add-name').focus(); }

  // ---- outputs -----------------------------------------------------------------------
  function procedure() {
    if (!result) return '';
    var rows = result.rows, L = computed(S.limiting);
    var solvents = rows.filter(function (r) { return r.role === 'solvent' && r.volume_ml; });
    var added = rows.filter(function (r) { return AMOUNT.indexOf(r.role) >= 0 && r.id !== S.limiting; });
    var text = '';
    var medium = solvents.length ? ' in ' + solvents.map(function (s) { return s.name + ' (' + volumeText(s.volume_ml) + ')'; }).join(' / ') + (result.totals.concentration_m ? ' (' + sig(result.totals.concentration_m, 2) + ' M)' : '') : '';
    if (added.length) text = 'To a solution of ' + L.name + ' ' + amountText(L) + medium + ' was added ' + added.map(function (r) { return r.name + ' ' + amountText(r); }).join(', ') + '.';
    else text = L.name + ' ' + amountText(L) + medium + '.';
    rows.filter(function (r) { return r.role === 'product'; }).forEach(function (p) {
      text += ' ' + (p.actual_mg !== null ? 'Isolated ' + p.name + ': ' + sig(p.actual_mg, 3) + ' mg (' + sig(p.yield_percent, 3) + '% of ' + sig(p.theory_mg, 3) + ' mg theoretical).' : 'Theoretical yield of ' + p.name + ': ' + sig(p.theory_mg, 3) + ' mg (' + sig(p.theory_mmol, 3) + ' mmol).');
    });
    return text;
  }
  function table(sep, markdown) {
    var lines = [], head = ['Species', 'Role', 'MW', 'equiv', 'mmol', 'mass (mg)', 'volume (mL)'];
    lines.push(head);
    result.rows.forEach(function (r) {
      if (r.role === 'product') lines.push([r.name, 'product (theoretical)', fmt(r.mw), '', fmt(r.theory_mmol), fmt(r.theory_mg), '']);
      else if (r.role === 'solvent') lines.push([r.name, 'solvent', fmt(r.mw), '', '', r.mass_mg === null ? '' : fmt(r.mass_mg), fmt(r.volume_ml)]);
      else lines.push([r.name, r.role + (r.id === S.limiting ? ' (limiting)' : ''), fmt(r.mw), fmt(r.equiv), fmt(r.mmol), fmt(r.mass_mg), fmt(r.volume_ml)]);
    });
    if (!markdown) return lines.map(function (l) { return l.join('\t'); }).join('\n');
    var out = ['| ' + lines[0].join(' | ') + ' |', '|' + lines[0].map(function (_, i) { return i < 2 ? ' --- |' : ' ---: |'; }).join('')];
    lines.slice(1).forEach(function (l) { out.push('| ' + l.join(' | ') + ' |'); });
    return out.join('\n');
  }
  function copy(text, label) {
    function fallback() {
      var area = el('textarea', { 'class': 'sr', 'aria-hidden': 'true' });
      area.value = text; area.style.position = 'fixed'; area.style.opacity = '0';
      document.body.appendChild(area); area.select();
      try { document.execCommand('copy'); say('Copied ' + label + '.', 'ok'); } catch (e) { say('Copy is blocked here; select the text and copy it by hand.', 'err'); }
      document.body.removeChild(area);
    }
    if (navigator.clipboard && window.isSecureContext !== false) navigator.clipboard.writeText(text).then(function () { say('Copied ' + label + '.', 'ok'); }, fallback);
    else fallback();
  }
  function download(name, text, type) {
    var a = el('a', { href: URL.createObjectURL(new Blob([text], { type: type })), download: name });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  // ---- local server ------------------------------------------------------------------
  function post(path, body) {
    return fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': API.token }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json(); });
  }
  function serverButtons() {
    var on = !!API;
    ['draw', 'load', 'scheme'].forEach(function (id) { $(id).disabled = !on; $(id).title = on ? '' : 'Start the calculator with cdx.py calc to draw in ChemDraw'; });
    if (!on) return;
    setInterval(function () { post('/api/ping').catch(function () {}); }, 15000);
    post('/api/ping').catch(function () {});
  }
  function plain(state) { return JSON.parse(JSON.stringify(state)); }

  // ---- wiring ------------------------------------------------------------------------
  $('undo').addEventListener('click', undo);
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z' && !/^(INPUT|TEXTAREA)$/.test((e.target || {}).tagName || '')) { e.preventDefault(); undo(); }
  });
  $('add').addEventListener('click', addFromInput);
  $('add-name').addEventListener('keydown', function (e) { if (e.key === 'Enter') addFromInput(); });
  $('copy-procedure').addEventListener('click', function () { if (result) copy(procedure(), 'the procedure text'); });
  $('copy-md').addEventListener('click', function () { if (result) copy(table(' | ', true), 'the Markdown table'); });
  $('copy-tsv').addEventListener('click', function () { if (result) copy(table('\t', false), 'the table for a spreadsheet'); });
  $('save').addEventListener('click', function () { download('reaction-calculator.json', JSON.stringify(S, null, 1), 'application/json'); });
  $('open-button').addEventListener('click', function () { $('open').click(); });
  $('open').addEventListener('change', function (e) {
    var file = e.target.files[0];
    if (!file) return;
    file.text().then(function (text) {
      var loaded = JSON.parse(text);
      loaded.rows.forEach(function (r) { r.svg = null; });
      var attempt = tryCompute(loaded);
      if (attempt.error) { say('That file is not a calculator state: ' + attempt.error, 'err'); return; }
      snapshot(); S = loaded; build(); say('Opened ' + file.name + '.', 'ok');
    }).catch(function () { say('That file is not a calculator state.', 'err'); });
    e.target.value = '';
  });
  $('print').addEventListener('click', function () { window.print(); });
  $('theme').addEventListener('click', function () {
    var root = document.documentElement;
    var dark = root.dataset.theme ? root.dataset.theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
  });
  $('draw').addEventListener('click', function () {
    say('Opening ChemDraw…', '', true);
    post('/api/canvas', { state: plain(S) }).then(function (r) {
      say(r.ok ? 'ChemDraw is open on ' + r.path + '. Draw the reaction, save it (Ctrl+S), then press Load drawing.' : (r.error || 'Could not open ChemDraw.'), r.ok ? 'ok' : 'err', true);
    }).catch(function () { say('The calculator server is not running any more.', 'err'); });
  });
  $('load').addEventListener('click', function () {
    say('Reading the drawing…', '', true);
    post('/api/canvas/load', { state: plain(S) }).then(function (r) {
      if (!r.ok) { say(r.error || 'Could not read the drawing.', 'err'); return; }
      snapshot(); S = r.state; build();
      say('Loaded ' + (r.summary || 'the drawing') + '. Amounts you had set were kept for structures that are still there.', 'ok');
    }).catch(function () { say('The calculator server is not running any more.', 'err'); });
  });
  $('scheme').addEventListener('click', function () {
    say('Writing the amounts into a scheme…', '', true);
    post('/api/scheme', { state: plain(S) }).then(function (r) {
      var missing = r.unplaced && r.unplaced.length ? ' Not drawn, so not labelled: ' + r.unplaced.join(', ') + '.' : '';
      say(r.ok ? 'A copy with the amounts is open in ChemDraw (' + r.path + ').' + missing : (r.error || 'Could not write the scheme.'), r.ok ? 'ok' : 'err', true);
    }).catch(function () { say('The calculator server is not running any more.', 'err'); });
  });
  $('title').addEventListener('change', function () { S.title = $('title').textContent.trim(); });
  $('add-name').placeholder = API ? 'Name, abbreviation, SMILES or formula' : 'Name (THF, Et3N) or formula (Pd(PPh3)4)';
  $('mode').textContent = API ? 'Connected to the local calculator server: drawing in ChemDraw and name lookup are on.' : 'Standalone page: drawing in ChemDraw and name lookup need the calculator server (cdx.py calc).';

  serverButtons();
  build();
})();
