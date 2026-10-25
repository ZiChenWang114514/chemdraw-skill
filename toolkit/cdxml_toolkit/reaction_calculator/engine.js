// Stoichiometry of one reaction; engine.py holds the same rules and the tests run both on the
// same cases. Units: mg, mmol, mL, g/mL, mol/L (= mmol/mL), g/mol. See engine.py for the model.
(function (root) {
  'use strict';

  var AMOUNT = ['reactant', 'reagent', 'catalyst'];
  var BASES = {
    reactant: ['equiv', 'mmol', 'mass', 'volume'],
    reagent: ['equiv', 'mmol', 'mass', 'volume'],
    catalyst: ['equiv', 'mmol', 'mass', 'volume'],
    solvent: ['volume', 'conc'],
    product: ['mass', 'yield', null]
  };

  function label(r) { return r.name || r.id; }

  function num(row, key, positive, fallback) {
    var v = row[key];
    if (v === undefined || v === null) v = fallback;
    if (v === undefined || v === null) return null;
    if (typeof v !== 'number' || !isFinite(v) || v < 0 || (positive && v === 0)) {
      throw new Error(label(row) + ': ' + key + ' must be a ' + (positive ? 'positive' : 'non-negative') + ' number');
    }
    return v;
  }

  function mmolOf(row) {
    var value = num(row, 'value', false), mw = num(row, 'mw', true), purity = num(row, 'purity', false, 1);
    if (!purity || purity > 1) throw new Error(label(row) + ': purity must be between 0 and 1');
    if (value === null) throw new Error(label(row) + ': the ' + row.basis + ' has no value');
    if (row.basis === 'mmol') return value;
    if (row.basis === 'mass') return value * purity / mw;
    var solution = num(row, 'solution_m', true), density = num(row, 'density', true);
    if (solution) return value * solution;
    if (density) return value * density * 1000 * purity / mw;
    throw new Error(label(row) + ': a volume needs a density or a solution molarity');
  }

  function copy(x) { return JSON.parse(JSON.stringify(x)); }

  function compute(state) {
    var rows = copy(state.rows || []), seen = {}, i, r;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      if (seen[r.id]) throw new Error('row ids must be unique');
      seen[r.id] = true;
    }
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      if (!BASES[r.role]) throw new Error(label(r) + ': role must be one of reactant, reagent, catalyst, solvent, product');
      var basis = r.basis === undefined ? null : r.basis;
      if (BASES[r.role].indexOf(basis) < 0) throw new Error(label(r) + ': a ' + r.role + ' cannot use basis ' + JSON.stringify(r.basis));
    }
    var limiting = null;
    for (i = 0; i < rows.length; i++) if (rows[i].id === state.limiting) limiting = rows[i];
    if (!limiting || AMOUNT.indexOf(limiting.role) < 0) throw new Error('limiting must name a reactant, reagent or catalyst row');
    if (limiting.basis === 'equiv') throw new Error('The limiting row sets the scale; give it mmol, mass or volume, not equiv');
    var base = mmolOf(limiting);
    if (base <= 0) throw new Error('The limiting row needs a positive amount');
    var warnings = [], solventMl = 0;
    rows.forEach(function (r) {
      var mw = num(r, 'mw', true);
      if (AMOUNT.indexOf(r.role) >= 0) {
        var mmol = r.basis === 'equiv' ? num(r, 'value', false) * base : mmolOf(r);
        var purity = num(r, 'purity', false, 1);
        r.mmol = mmol;
        r.equiv = mmol / base;
        r.mass_mg = mmol * mw / purity;
        var solution = num(r, 'solution_m', true), density = num(r, 'density', true);
        r.volume_ml = solution ? mmol / solution : (density ? r.mass_mg / 1000 / density : null);
      } else if (r.role === 'solvent') {
        var value = num(r, 'value', false);
        if (value === null || (r.basis === 'conc' && value === 0)) throw new Error(label(r) + ': the ' + r.basis + ' needs a positive value');
        r.volume_ml = r.basis === 'volume' ? value : base / value;
        var d = num(r, 'density', true);
        r.mass_mg = d ? r.volume_ml * d * 1000 : null;
        solventMl += r.volume_ml;
      }
    });
    var first = limiting.coefficient ? limiting.coefficient : 1;
    rows.forEach(function (r) {
      if (r.role !== 'product') return;
      var coefficient = num(r, 'coefficient', true, 1), mw = num(r, 'mw', true);
      r.theory_mmol = base * coefficient / first;
      r.theory_mg = r.theory_mmol * mw;
      r.actual_mg = null;
      r.yield_percent = null;
      var value = num(r, 'value', false);
      if (r.basis === 'mass' && value !== null) {
        r.actual_mg = value;
        r.yield_percent = value / r.theory_mg * 100;
      } else if (r.basis === 'yield' && value !== null) {
        r.yield_percent = value;
        r.actual_mg = r.theory_mg * value / 100;
      }
      if (r.yield_percent !== null && r.yield_percent > 100) {
        warnings.push(label(r) + ': yield above 100% (wet or impure product, or a wrong limiting reagent or molecular weight)');
      }
    });
    var reactants = rows.filter(function (r) { return r.role === 'reactant'; });
    var products = rows.filter(function (r) { return r.role === 'product'; });
    var input = 0;
    rows.forEach(function (r) { if (AMOUNT.indexOf(r.role) >= 0) input += r.mass_mg; });
    var totals = {
      concentration_m: solventMl ? base / solventMl : null,
      solvent_ml: solventMl || null,
      limiting_mmol: base,
      input_mg: input
    };
    var reactantMass = 0, weighed = 0;
    reactants.forEach(function (r) {
      reactantMass += r.mw * num(r, 'coefficient', true, 1);
      weighed += r.mass_mg;
    });
    if (products.length && reactantMass) {
      var main = products[0];
      totals.atom_economy_percent = main.mw * num(main, 'coefficient', true, 1) / reactantMass * 100;
      if (main.actual_mg !== null) totals.reaction_mass_efficiency_percent = main.actual_mg / weighed * 100;
    }
    return { limiting: limiting.id, rows: rows, totals: totals, warnings: warnings };
  }

  function rebase(state, newLimiting) {
    var result = compute(state), byId = {};
    result.rows.forEach(function (r) { byId[r.id] = r; });
    if (!byId[newLimiting] || AMOUNT.indexOf(byId[newLimiting].role) < 0) throw new Error('limiting must name a reactant, reagent or catalyst row');
    var base = byId[newLimiting].mmol, out = copy(state);
    out.rows.forEach(function (r) {
      var c = byId[r.id];
      if (AMOUNT.indexOf(r.role) >= 0 && r.basis === 'equiv') r.value = c.mmol / base;
      else if (r.role === 'solvent' && r.basis === 'conc') { r.basis = 'volume'; r.value = c.volume_ml; }
    });
    out.rows.forEach(function (r) {
      if (r.id === newLimiting && r.basis === 'equiv') { r.basis = 'mmol'; r.value = byId[newLimiting].mmol; }
    });
    out.limiting = newLimiting;
    return out;
  }

  // Molecular weight of a typed formula such as C6H12O6, Pd(PPh3)4 or CuSO4.5H2O (conventional atomic weights).
  var WEIGHTS = {
    H: 1.008, Li: 6.94, Be: 9.0122, B: 10.81, C: 12.011, N: 14.007, O: 15.999, F: 18.998, Na: 22.990, Mg: 24.305,
    Al: 26.982, Si: 28.085, P: 30.974, S: 32.06, Cl: 35.45, K: 39.098, Ca: 40.078, Ti: 47.867, V: 50.942, Cr: 51.996,
    Mn: 54.938, Fe: 55.845, Co: 58.933, Ni: 58.693, Cu: 63.546, Zn: 65.38, Ga: 69.723, Ge: 72.630, As: 74.922,
    Se: 78.971, Br: 79.904, Rb: 85.468, Sr: 87.62, Zr: 91.224, Mo: 95.95, Ru: 101.07, Rh: 102.91, Pd: 106.42,
    Ag: 107.87, Cd: 112.41, Sn: 118.71, Sb: 121.76, Te: 127.60, I: 126.90, Cs: 132.91, Ba: 137.33, W: 183.84,
    Os: 190.23, Ir: 192.22, Pt: 195.08, Au: 196.97, Hg: 200.59, Pb: 207.2, Bi: 208.98
  };
  var GROUPS = { Me: 'CH3', Et: 'C2H5', Pr: 'C3H7', Bu: 'C4H9', Ph: 'C6H5', Bn: 'C7H7', Ac: 'C2H3O', Cy: 'C6H11' };

  function formulaWeight(text) {
    var s = String(text).replace(/[·•*]/g, '.').replace(/\s+/g, '');
    if (!s) return null;
    var pos = 0;
    function parseGroup(close) {
      var total = 0;
      while (pos < s.length) {
        var ch = s[pos];
        if (ch === close) return total;
        var unit, m;
        if (ch === '(') {
          pos++;
          unit = parseGroup(')');
          if (s[pos] !== ')') return NaN;
          pos++;
        } else {
          m = /^[A-Z][a-z]?/.exec(s.slice(pos));
          if (!m) return NaN;
          var sym = m[0];
          if (!(sym in WEIGHTS) && !(sym in GROUPS) && sym.length === 2 && sym[1] in WEIGHTS === false) sym = sym[0];
          if (sym in GROUPS) { unit = formulaWeight(GROUPS[sym]); pos += sym.length; }
          else if (sym in WEIGHTS) { unit = WEIGHTS[sym]; pos += sym.length; }
          else return NaN;
        }
        var n = /^\d+/.exec(s.slice(pos));
        if (n) pos += n[0].length;
        total += unit * (n ? parseInt(n[0], 10) : 1);
      }
      return total;
    }
    var parts = s.split('.'), sum = 0, k;
    for (k = 0; k < parts.length; k++) {
      var lead = /^(\d+)(.*)$/.exec(parts[k]), mult = 1, body = parts[k];
      if (k > 0 && lead) { mult = parseInt(lead[1], 10); body = lead[2]; }
      s = body; pos = 0;
      var w = parseGroup(null);
      if (!isFinite(w) || pos !== s.length) return null;
      sum += mult * w;
    }
    return sum;
  }

  var api = { compute: compute, rebase: rebase, formulaWeight: formulaWeight };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CalcEngine = api;
})(typeof window !== 'undefined' ? window : this);
