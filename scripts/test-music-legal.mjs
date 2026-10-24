import { validateLegalPage } from './music-legal-validation.mjs';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
const read = p => readFileSync(new URL('../public/music-transfer/' + p, import.meta.url), 'utf8');
for (const path of ['index.html', 'privacy/index.html', 'terms/index.html']) {
  test(path + ' is accessible, linked, and excludes private audit material', () => {
    const html = read(path);
    validateLegalPage(html);
  });
}
test('privacy discloses Google, Codex, local storage and deletion obligations', () => {
  const html = read('privacy/index.html');
  for (const fragment of ['policies.google.com/privacy', 'myaccount.google.com/permissions', 'api-services-user-data-policy', 'OpenAI Codex', '30 calendar days', 'seven calendar days', 'at least weekly', 'YouTube playlists']) assert.ok(html.includes(fragment), fragment);
});
test('terms identify private use and binding YouTube terms', () => {
  const html = read('terms/index.html');
  assert.ok(html.includes('Using the client means agreeing'));
  assert.ok(html.includes('www.youtube.com/t/terms'));
  assert.ok(html.includes('uncertain or unavailable') || html.includes('uncertain or unavailable'.replace('uncertain', 'Uncertain')));
});

test('validator rejects missing links, private data, scripts and paragraph headings', () => {
  const html=read('privacy/index.html');
  for (const bad of [html.replaceAll('/music-transfer/privacy/','/missing/'), html+'<p>refresh_token=synthetic</p>', html+'<script>unwanted()</script>', html+'<h2>Heading\nparagraph</h2>']) assert.throws(() => validateLegalPage(bad));
});
