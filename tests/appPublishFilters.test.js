const fs = require('fs');
const path = require('path');

const APP_SRC = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');

describe('public Proton Pulse config queries', () => {
  test('public app surfaces only request explicitly published cloud configs', () => {
    expect(APP_SRC).toContain('user_proton_configs?is_published=eq.true');
    expect(APP_SRC).toContain("url.searchParams.set('is_published', 'eq.true')");
    expect(APP_SRC).toContain('user_proton_configs?app_id=eq.${appId}&is_published=eq.true');
  });
});
