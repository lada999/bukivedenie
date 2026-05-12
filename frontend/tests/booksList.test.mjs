import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildTokenSummary, pickPrimaryTextFile, pickTokensFile } from '../src/views/booksList.js'

test('dashboard helpers prefer the canonical token file and summarize rows', () => {
  assert.equal(pickTokensFile(['notes.txt', 'tokens.csv', 'other.csv']), 'tokens.csv')
  assert.equal(pickTokensFile(['chapter_tokens.csv', 'notes.txt']), 'chapter_tokens.csv')
  assert.deepEqual(buildTokenSummary([
    ['alpha', '12'],
    ['beta', 4],
    ['gamma', null],
  ]), [
    { token: 'alpha', count: 12 },
    { token: 'beta', count: 4 },
    { token: 'gamma', count: 0 },
  ])
})

test('dashboard picks the first text-like file for the shared preview', () => {
  assert.equal(pickPrimaryTextFile(['notes.csv', 'chapter-1.txt', 'appendix.md']), 'chapter-1.txt')
  assert.equal(pickPrimaryTextFile(['tables.csv', 'data.json']), '')
})
