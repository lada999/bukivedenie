import { api } from '../api.js'

export async function viewBookOverview(book){
  const el = document.getElementById('view')
  if(!el){
    console.error('view mount not found in viewBookOverview')
    return
  }
  el.innerHTML = `<h2>${book}</h2><p>Загружаю обзор…</p>`
  // Пытаемся взять базовые файлы
  const files = await api.files(book).then(r=>r.files||[]).catch(()=>[])
  const hasTokens = files.includes('tokens.csv') || files.some(f=>f.endsWith('_tokens.csv'))
  const hasSent = files.includes('sentiment_by_chapter.csv')
  const hasCooc = files.includes('cooccurrence_edges.csv')

  el.innerHTML = `
    <hgroup>
      <h2>${book}</h2>
      <p>Быстрые действия</p>
    </hgroup>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
      <a class="contrast" href="#/book/${encodeURIComponent(book)}/viz/tokens">Tokens</a>
      <a class="contrast" href="#/book/${encodeURIComponent(book)}/viz/wordcloud">Word Cloud</a>
      <a class="contrast" href="#/book/${encodeURIComponent(book)}/viz/network">Network</a>
      <a class="contrast" href="#/book/${encodeURIComponent(book)}/viz/sentiment">Sentiment</a>
      <a class="contrast" href="#/book/${encodeURIComponent(book)}/viz/heatmap">Heatmap</a>
      <a class="secondary" href="#/book/${encodeURIComponent(book)}/files">Files</a>
    </div>
    <details style="margin-top:12px;">
      <summary>Файлы</summary>
      <pre style="white-space:pre-wrap;">${files.map(f=>`- ${f}`).join('\n')}</pre>
    </details>
  `
}
