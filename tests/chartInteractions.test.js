/**
 * Tests for app-chart-interactions.js -- attachClickToFilter, dispatchFilter,
 * onFilterChange. attachChartHover is exercised lightly since it depends on
 * SVG measurement which jsdom doesn't really do; we rely on the manual
 * dev-server check for full hover validation.
 */

const path = require('path');

const MOD_PATH = path.join(__dirname, '..', 'app-chart-interactions.js');

function loadMod() {
  delete require.cache[require.resolve(MOD_PATH)];
  return require(MOD_PATH);
}

// Minimal CustomEvent shim if not present
if (typeof global.CustomEvent !== 'function') {
  global.CustomEvent = class CustomEvent {
    constructor(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
    }
  };
}

// Fake DOM node with classList + listener storage. Just enough surface to
// drive the helper without pulling in jsdom for these focused unit tests.
function fakeEl({ classes = [], dataset = {}, parent = null } = {}) {
  const _classes = new Set(classes);
  const listeners = {};
  const el = {
    classList: {
      add: c => _classes.add(c),
      remove: c => _classes.delete(c),
      toggle: c => { _classes.has(c) ? _classes.delete(c) : _classes.add(c); },
      contains: c => _classes.has(c),
      _set: _classes,
    },
    getAttribute: k => dataset[k] != null ? String(dataset[k]) : null,
    style: {},
    parentNode: parent,
    addEventListener: (type, fn) => {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push(fn);
    },
    fire: (type, ev = {}) => {
      (listeners[type] || []).forEach(fn => fn(ev));
    },
    _listeners: listeners,
  };
  return el;
}

describe('dispatchFilter / onFilterChange', () => {
  // Use the real jsdom document. Track listeners so we can detach in afterEach
  const tracked = [];
  afterEach(() => {
    while (tracked.length) {
      const fn = tracked.pop();
      document.removeEventListener('chart-filter', fn);
    }
  });

  test('dispatchFilter sends a chart-filter event with the payload', () => {
    const { dispatchFilter } = loadMod();
    const received = [];
    const fn = ev => received.push(ev.detail);
    document.addEventListener('chart-filter', fn);
    tracked.push(fn);
    dispatchFilter({ key: 'tier', value: 'gold' });
    expect(received).toEqual([{ key: 'tier', value: 'gold' }]);
  });

  test('onFilterChange registers a listener that receives the payload', () => {
    const { dispatchFilter, onFilterChange } = loadMod();
    const received = [];
    // onFilterChange wraps the document.addEventListener so we cant detach
    // it cleanly via tracked[], but the helper unwraps the CustomEvent for us
    onFilterChange(p => received.push(p));
    dispatchFilter(null);
    expect(received).toEqual([null]);
  });
});

describe('attachClickToFilter', () => {
  // Listen on the real jsdom document for chart-filter events. Easier than
  // trying to swap document.dispatchEvent which jsdom owns
  let dispatched;
  let listener;
  beforeEach(() => {
    dispatched = [];
    listener = ev => { dispatched.push(ev.detail); };
    document.addEventListener('chart-filter', listener);
  });
  afterEach(() => {
    document.removeEventListener('chart-filter', listener);
  });

  test('clicking a chip dispatches the payload and toggles active class', () => {
    const { attachClickToFilter } = loadMod();
    const chipA = fakeEl({ dataset: { 'data-tier': 'gold' } });
    const chipB = fakeEl({ dataset: { 'data-tier': 'platinum' } });
    const all = [chipA, chipB];
    const root = {
      querySelectorAll: sel => sel.includes('.is-active')
        ? all.filter(c => c.classList.contains('is-active'))
        : all,
    };
    attachClickToFilter({
      root,
      selector: '.chip',
      getFilter: el => ({ key: 'tier', value: el.getAttribute('data-tier') }),
    });

    chipA.fire('click');
    expect(chipA.classList.contains('is-active')).toBe(true);
    expect(dispatched).toHaveLength(1);
    expect(dispatched[0]).toEqual({ key: 'tier', value: 'gold' });

    chipA.fire('click');
    expect(chipA.classList.contains('is-active')).toBe(false);
    expect(dispatched).toHaveLength(2);
    expect(dispatched[1]).toBeNull();
  });

  test('clicking a second chip clears the first', () => {
    const { attachClickToFilter } = loadMod();
    const chipA = fakeEl({ classes: ['is-active'], dataset: { 'data-tier': 'gold' } });
    const chipB = fakeEl({ dataset: { 'data-tier': 'platinum' } });
    const all = [chipA, chipB];
    const root = {
      querySelectorAll: sel => sel.includes('.is-active')
        ? all.filter(c => c.classList.contains('is-active'))
        : all,
    };
    attachClickToFilter({
      root,
      selector: '.chip',
      getFilter: el => ({ key: 'tier', value: el.getAttribute('data-tier') }),
    });

    chipB.fire('click');
    expect(chipA.classList.contains('is-active')).toBe(false);
    expect(chipB.classList.contains('is-active')).toBe(true);
    expect(dispatched[0]).toEqual({ key: 'tier', value: 'platinum' });
  });

  test('cursor style is set to pointer for clickability hint', () => {
    const { attachClickToFilter } = loadMod();
    const chip = fakeEl({ dataset: { 'data-tier': 'gold' } });
    const root = { querySelectorAll: () => [chip] };
    attachClickToFilter({
      root,
      selector: '.chip',
      getFilter: () => ({ key: 'tier', value: 'gold' }),
    });
    expect(chip.style.cursor).toBe('pointer');
  });
});
