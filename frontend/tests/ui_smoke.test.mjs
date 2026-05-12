import assert from 'node:assert/strict'
import { test } from 'node:test'
import { BROWSER_PATH_CANDIDATES, DEFAULT_OUT_DIR, ROUTES, artifactPaths, browserLaunchArgs, launchBrowser, routeUrl, slugify } from '../../scripts/ui_smoke.mjs'

test('smoke route manifest stays stable', () => {
  const dashboard = ROUTES.find(route => route.name === 'dashboard')
  const fileRoute = ROUTES.find(route => route.name === 'file')

  assert.ok(ROUTES.length >= 6)
  assert.equal(ROUTES[0].name, 'dashboard')
  assert.equal(ROUTES[0].kind, 'dashboard')
  assert.deepEqual(dashboard, {
    name: 'dashboard',
    hash: '#/book/{book}',
    kind: 'dashboard',
    ready: '#view hgroup, #view details, #view a.contrast',
  })
  assert.equal(fileRoute?.ready, '#view table, #view pre')
  assert.equal(slugify('Heatmap / token × chapter'), 'heatmap-token-chapter')
  assert.equal(routeUrl('http://127.0.0.1:8000', ROUTES[0], 'book-a', 'file.csv'), 'http://127.0.0.1:8000/#/book/book-a')
  assert.equal(DEFAULT_OUT_DIR, 'artifacts/ui-smoke')
  assert.ok(BROWSER_PATH_CANDIDATES.includes('/data/data/com.termux/files/usr/bin/chromium'))
  assert.deepEqual(artifactPaths('/tmp/out', 'dashboard', 'Book Atlas'), {
    htmlPath: '/tmp/out/html/book-atlas__dashboard.html',
    screenshotPath: '/tmp/out/screens/book-atlas__dashboard.png',
  })
  assert.deepEqual(artifactPaths('/tmp/out', 'file', 'Book Atlas'), {
    htmlPath: '/tmp/out/html/book-atlas__file.html',
    screenshotPath: '/tmp/out/screens/book-atlas__file.png',
  })
  assert.equal(browserLaunchArgs('/usr/bin/chromium', true).headless, false)
})

test('browser launch helper falls back cleanly when launch fails', async () => {
  const browser = await launchBrowser({ launch: async () => { throw new Error('boom') } }, '/usr/bin/chromium', false)
  assert.equal(browser, null)
})
