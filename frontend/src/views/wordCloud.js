import { api } from '../api.js'
import WordCloud from 'wordcloud'

export async function viewWordCloud(book){
  const el = document.getElementById('view')
  if(!el){
    console.error('view mount not found in viewWordCloud')
    return
  }
  el.innerHTML = `<h2>${book}: Word Cloud</h2><p>Загружаю…</p>`
  const files = await api.files(book).then(r=>r.files||[])
  const name = files.includes('tokens.csv') ? 'tokens.csv' : (files.find(f=>f.endsWith('_tokens.csv')) || 'tokens.csv')
  const { type, rows=[] } = await api.fileParsed(book, name)
  if(type !== 'csv' || !rows.length){
    el.innerHTML = `<h2>${book}: Word Cloud</h2><p>Нет данных</p>`
    return
  }
  const words = rows.slice(0,200).map(r => [r[0], Math.max(12, Math.min(80, +r[1]))])
  el.innerHTML = `<div id="cloud" style="width:100%; min-height:420px;"></div>`
  try{
    WordCloud(document.getElementById('cloud'), { list: words, backgroundColor: '#fff' })
  }catch(e){
    console.error('WordCloud render failed', e)
    el.innerHTML = `<p>WordCloud render failed</p>`
  }
}
