import assert from 'node:assert/strict';
export function validateLegalPage(html) {
  for (const fragment of ['<html lang="en">', 'name="viewport"', '<h1>', '/music-transfer/privacy/', '/music-transfer/terms/']) {
    assert.ok(html.includes(fragment), 'Missing accessible document structure or policy link: ' + fragment);
  }
  assert.doesNotMatch(html, /\b\d{5}(?:-\d{4})?\b|refresh_token|client_secret|DRAFT FOR REVIEW|quota-applicant/i);
  assert.doesNotMatch(html, /<script|<iframe|<img[^>]+https:/i);
  for (const h of html.matchAll(/<h2>([\s\S]*?)<\/h2>/g)) {
    assert.ok(h[1].length < 150 && !h[1].includes('\n'), 'Heading must not contain body paragraphs');
  }
}
