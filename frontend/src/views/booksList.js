import { api } from '../api.js'

const WIDGETS = [
  { key: 'atlas', title: 'Book Atlas', description: 'Selected-book map, file counts, and fast routes.' },
  { key: 'viewer', title: 'Text Viewer', description: 'Preview the current source text and linked fragments.' },
  { key: 'tokens', title: 'Top Tokens', description: 'High-signal words in a compact bar chart.' },
  { key: 'wordcloud', title: 'Word Cloud', description: 'Loose lexical scan for the book vocabulary.' },
  { key: 'network', title: 'Character Network', description: 'Relationship graph with its own scroll.' },
  { key: 'sentiment', title: 'Sentiment', description: 'Chapter-by-chapter sentiment drift.' },
  { key: 'heatmap', title: 'Heatmap', description: 'Token density across chapters.' },
  { key: 'files', title: 'Files', description: 'Raw inputs and generated artifacts.' },
]

function escapeHtml(value){
  return String(value).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
}

function selectedBookFromInput(book, books){
  if(book && books.includes(book)) return book
  return books[0] || ''
}

function bookHref(book){
  return `#/books/${encodeURIComponent(book)}`
}

function widgetHref(book, key){
  if(key === 'atlas') return `#/books/${encodeURIComponent(book)}`
  if(key === 'files') return `#/book/${encodeURIComponent(book)}/files`
  return `#/book/${encodeURIComponent(book)}/viz/${key}`
}

function isTextLikeFile(name){
  return /(^|[._-])(text|txt|transcript|excerpt)([._-]|\.|$)/i.test(name)
    || /\.(txt|md|markdown|jsonl)$/i.test(name)
}

export function pickPrimaryTextFile(files){
  const list = files || []
  return list.find(isTextLikeFile)
    || list.find(name => !/\.(csv|tsv|json|jsonl|parquet)$/i.test(name))
    || ''
}

function previewText(value){
  return String(value || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .filter(Boolean)
    .slice(0, 12)
    .join('\n')
}

export function pickTokensFile(files){
  return files.includes('tokens.csv') ? 'tokens.csv' : (files.find(f => f.endsWith('_tokens.csv')) || '')
}

export function buildTokenSummary(rows, limit=5){
  return (rows || []).slice(0, limit).map(row => ({
    token: String(row?.[0] ?? ''),
    count: Number(row?.[1] ?? 0) || 0,
  }))
}

export async function viewBooks(book=''){
  const mount = document.getElementById('view')
  if(!mount){
    console.error('view mount not found in viewBooks')
    return
  }
  mount.innerHTML = '<p>Загружаю список книг…</p>'
  const { books } = await api.books()
  const visibleBooks = (books || []).filter(b => !['processed', 'tables', '__pycache__'].includes(b))
  if(!visibleBooks?.length){
    mount.innerHTML = '<p>Книги не найдены. Добавьте raw-файлы и запустите анализ.</p>'
    return
  }
  const selected = selectedBookFromInput(book, visibleBooks)
  const selectedFiles = await api.files(selected).then(r => r.files || []).catch(() => [])
  const textFiles = selectedFiles.filter(isTextLikeFile)
  const primaryTextFile = pickPrimaryTextFile(selectedFiles)
  const tokensFile = pickTokensFile(selectedFiles)
  const fileCountText = selectedFiles.length === 1 ? '1 file available' : `${selectedFiles.length} files available`
  const textCountText = textFiles.length === 1 ? '1 text fragment' : `${textFiles.length} text fragments`
  const tokenSummary = tokensFile
    ? await api.fileParsed(selected, tokensFile)
      .then(resp => resp?.type === 'csv' ? buildTokenSummary(resp.rows || []) : [])
      .catch(() => [])
    : []
  const textPreview = primaryTextFile
    ? await api.fileParsed(selected, primaryTextFile)
      .then(resp => previewText(resp?.content ?? resp?.data ?? '')).catch(() => '')
    : ''
  const widgets = WIDGETS.map(widget => `
    <section class="dashboard-widget dashboard-widget--${widget.key}">
      <header class="dashboard-widget__header">
        <div class="dashboard-widget__heading">
          <h3>${widget.title}</h3>
          <p>${widget.description}</p>
        </div>
        <a class="dashboard-widget__link" href="${widgetHref(selected, widget.key)}">Open</a>
      </header>
      <div class="dashboard-widget__body">
        ${widget.key === 'atlas' ? `
          <div class="dashboard-atlas">
            <div class="dashboard-atlas__selected">Selected book</div>
            <a class="dashboard-atlas__book" href="${bookHref(selected)}">${escapeHtml(selected)}</a>
            <p>${selectedFiles.length ? `${fileCountText}.` : 'No files available yet.'} ${textFiles.length ? `${textCountText}.` : 'No text fragments detected yet.'}</p>
            <div class="dashboard-atlas__stats">
              <span>${fileCountText}</span>
              <span>${textCountText}</span>
              <span>${primaryTextFile ? 'Preview ready' : 'No preview source'}</span>
            </div>
            ${primaryTextFile ? `
              <div class="dashboard-atlas__preview">
                <div class="dashboard-text-viewer__meta">Primary text</div>
                <a href="#/book/${encodeURIComponent(selected)}/file/${encodeURIComponent(primaryTextFile)}">${escapeHtml(primaryTextFile)}</a>
                ${textPreview ? `<pre>${escapeHtml(textPreview)}</pre>` : ''}
              </div>
            ` : ''}
            <div class="dashboard-atlas__fragments">
              <strong>Text fragments</strong>
              ${textFiles.length ? `
                <ul class="dashboard-fragment-list">
                  ${textFiles.slice(0, 4).map(name => `
                    <li><a href="#/book/${encodeURIComponent(selected)}/file/${encodeURIComponent(name)}">${escapeHtml(name)}</a></li>
                  `).join('')}
                </ul>
              ` : '<p>No text-like fragment files detected.</p>'}
            </div>
          </div>
        ` : widget.key === 'viewer' ? `
          <div class="dashboard-text-viewer">
            <div class="dashboard-text-viewer__meta">
              ${primaryTextFile ? `
                <span>Selected book: <a href="${bookHref(selected)}">${escapeHtml(selected)}</a></span>
                <span>Source file: <a href="#/book/${encodeURIComponent(selected)}/file/${encodeURIComponent(primaryTextFile)}">${escapeHtml(primaryTextFile)}</a></span>
                <a class="dashboard-widget__link" href="#/book/${encodeURIComponent(selected)}/file/${encodeURIComponent(primaryTextFile)}">Open in viewer</a>
              ` : 'No text source detected yet.'}
            </div>
            ${textPreview ? `<pre>${escapeHtml(textPreview)}</pre>` : '<p>Open a text-like file from the atlas to inspect fragments.</p>'}
          </div>
        ` : widget.key === 'tokens' ? `
          <div class="dashboard-token-summary">
            <div class="dashboard-text-viewer__meta">
              ${tokensFile ? `Linked file: <a href="#/book/${encodeURIComponent(selected)}/viz/tokens">${escapeHtml(tokensFile)}</a>` : 'No token file detected yet.'}
            </div>
            ${tokenSummary.length ? `
              <ul class="dashboard-fragment-list">
                ${tokenSummary.map(({ token, count }) => `
                  <li><strong>${escapeHtml(token)}</strong> <span>${count}</span></li>
                `).join('')}
              </ul>
            ` : '<p>Token data is not available for this book yet.</p>'}
          </div>
        ` : `
          <div class="dashboard-widget__empty">Open ${escapeHtml(widget.title)} to inspect ${escapeHtml(selected)}.</div>
        `}
      </div>
    </section>
  `).join('')
  const bookItems = visibleBooks.map(b => `
    <a class="book-chip${b === selected ? ' is-active' : ''}" href="${bookHref(b)}">
      <strong>${escapeHtml(b)}</strong>
      <span>${b === selected ? 'Active' : 'Book'}</span>
    </a>
  `).join('')
  mount.innerHTML = `
    <section class="dashboard-shell">
      <aside class="dashboard-books">
        <hgroup>
          <h2>Книги</h2>
          <p>Selected atlas: ${escapeHtml(selected)}</p>
        </hgroup>
        <div class="book-chip-list">${bookItems}</div>
      </aside>
      <section class="dashboard-main">
        <header class="dashboard-hero">
          <hgroup>
            <h2>${escapeHtml(selected)}</h2>
            <p>Atlas view for the selected book. Jump into files or open a widget below.</p>
          </hgroup>
          <a class="dashboard-widget__link" href="#/book/${encodeURIComponent(selected)}">Book overview</a>
        </header>
        <div class="dashboard-grid">${widgets}</div>
      </section>
    </section>
  `
}
