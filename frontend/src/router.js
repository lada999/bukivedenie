import { viewBooks } from './views/booksList.js'
import { viewBookOverview } from './views/bookOverview.js'
import { viewFiles } from './views/filesList.js'
import { viewFile } from './views/fileViewer.js'
import { viewTokens } from './views/tokensChart.js'
import { viewWordCloud } from './views/wordCloud.js'
import { viewNetwork } from './views/networkGraph.js'
import { viewSentiment } from './views/sentimentChart.js'
import { viewHeatmap } from './views/heatmap.js'

function parseHash(){
  const h = location.hash || '#/books'
  const parts = h.slice(2).split('/') // remove #/
  return parts
}

export function initRouter(){
  window.addEventListener('hashchange', render)
  render()
}

function setView(html){
  const v = document.getElementById('view')
  if(!v){
    console.error('view container not found')
    return
  }
  v.innerHTML = html
}

function emitRoute(route, view){
  try{
    const detail = { route, view, ts: new Date().toISOString() }
    window.__ROUTE__ = detail
    window.dispatchEvent(new CustomEvent('app:route', { detail }))
  }catch(e){ /* ignore */ }
}

function viewAbout(){
  setView(`
    <hgroup>
      <h2>О проекте</h2>
      <p>Минимальный интерфейс для текстовой аналитики</p>
    </hgroup>
    <p>Доступны списки книг, таблицы файлов, токены, облако, граф связей, сентимент и теплокарта.</p>
  `)
}

async function render(){
  const p = parseHash()
  try{
    if(p[0] === '' || p[0] === 'books'){
      emitRoute(location.hash || '#/books', 'books')
      return viewBooks(p[1] ? decodeURIComponent(p[1]) : '')
    }
    if(p[0] === 'about'){
      emitRoute(location.hash || '#/about', 'about')
      return viewAbout()
    }
    if(p[0] === 'book' && p[1]){
      const book = decodeURIComponent(p[1])
      if(p[2] === 'files'){
        emitRoute(location.hash, 'files')
        return viewFiles(book)
      }
      if(p[2] === 'file' && p[3]){
        emitRoute(location.hash, 'file')
        return viewFile(book, decodeURIComponent(p[3]))
      }
      if(p[2] === 'viz' && p[3] === 'tokens'){
        emitRoute(location.hash, 'tokens')
        return viewTokens(book)
      }
      if(p[2] === 'viz' && p[3] === 'wordcloud'){
        emitRoute(location.hash, 'wordcloud')
        return viewWordCloud(book)
      }
      if(p[2] === 'viz' && p[3] === 'network'){
        emitRoute(location.hash, 'network')
        return viewNetwork(book)
      }
      if(p[2] === 'viz' && p[3] === 'sentiment'){
        emitRoute(location.hash, 'sentiment')
        return viewSentiment(book)
      }
      if(p[2] === 'viz' && p[3] === 'heatmap'){
        emitRoute(location.hash, 'heatmap')
        return viewHeatmap(book)
      }
      emitRoute(location.hash, 'overview')
      return viewBookOverview(book)
    }
    emitRoute(location.hash || '#/books', 'not-found')
    setView('<div>Not found</div>')
  }catch(e){
    console.error(e)
    setView(`<pre style="white-space:pre-wrap;color:#c00;">${e?.message||e}</pre>`)
  }
}
