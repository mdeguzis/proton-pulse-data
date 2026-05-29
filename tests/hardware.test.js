/**
 * Tests for app-hardware.js -- the shared loadMyHardware helper that returns
 * either saved profile hardware or a Steam Deck preview fallback.
 */

const path = require('path');

// jsdom-like localStorage shim. Each test gets a fresh one.
function makeStorage() {
  const store = {};
  return {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
    clear: () => { for (const k of Object.keys(store)) delete store[k]; },
    _raw: store,
  };
}

// require() the module, then patch the localStorage global the script
// expects. The module checks `localStorage` directly at call time so we
// can swap it per test.
const HW_MOD_PATH = path.join(__dirname, '..', 'app-hardware.js');

function loadMod() {
  // Clear require cache so each test starts fresh
  delete require.cache[require.resolve(HW_MOD_PATH)];
  return require(HW_MOD_PATH);
}

describe('loadMyHardware', () => {
  beforeEach(() => {
    global.localStorage = makeStorage();
  });
  afterEach(() => {
    delete global.localStorage;
  });

  test('returns saved hardware when gpu is set', () => {
    global.localStorage.setItem('proton-pulse:myhw:gpu', 'RTX 4090');
    global.localStorage.setItem('proton-pulse:myhw:gpu-vendor', 'NVIDIA');
    global.localStorage.setItem('proton-pulse:myhw:os', 'Arch');
    global.localStorage.setItem('proton-pulse:myhw:kernel', '6.10.0');
    const { loadMyHardware, isPreviewHardware } = loadMod();
    const hw = loadMyHardware();
    expect(hw.gpu).toBe('RTX 4090');
    expect(hw.gpuVendor).toBe('NVIDIA');
    expect(isPreviewHardware(hw)).toBe(false);
  });

  test('returns saved hardware when only os is set', () => {
    global.localStorage.setItem('proton-pulse:myhw:os', 'Fedora');
    const { loadMyHardware, isPreviewHardware } = loadMod();
    const hw = loadMyHardware();
    expect(hw.os).toBe('Fedora');
    expect(isPreviewHardware(hw)).toBe(false);
  });

  test('falls back to Steam Deck preview when nothing saved', () => {
    const { loadMyHardware, isPreviewHardware, STEAM_DECK_HW } = loadMod();
    const hw = loadMyHardware();
    expect(isPreviewHardware(hw)).toBe(true);
    expect(hw.gpuVendor).toBe('AMD');
    expect(hw.os).toBe(STEAM_DECK_HW.os);
  });

  test('Steam Deck preview has a kernel set so kernel-match scoring fires', () => {
    const { loadMyHardware } = loadMod();
    const hw = loadMyHardware();
    expect(hw.kernel).toBeTruthy();
    expect(hw.kernel).toMatch(/^\d+\./);
  });

  test('survives localStorage throwing (private browsing)', () => {
    global.localStorage = {
      getItem: () => { throw new Error('SecurityError'); },
      setItem: () => { throw new Error('SecurityError'); },
    };
    const { loadMyHardware, isPreviewHardware } = loadMod();
    const hw = loadMyHardware();
    expect(isPreviewHardware(hw)).toBe(true);
    expect(hw.gpuVendor).toBe('AMD');
  });

  test('isPreviewHardware handles null/undefined safely', () => {
    const { isPreviewHardware } = loadMod();
    expect(isPreviewHardware(null)).toBe(false);
    expect(isPreviewHardware(undefined)).toBe(false);
    expect(isPreviewHardware({})).toBe(false);
  });
});

describe('renderPreviewHardwareBanner', () => {
  test('returns a non-empty html string mentioning Steam Deck + profile link', () => {
    const { renderPreviewHardwareBanner } = loadMod();
    const html = renderPreviewHardwareBanner();
    expect(html).toContain('Steam Deck');
    expect(html).toContain('profile.html');
    expect(html).toContain('hw-preview-banner');
  });
});
