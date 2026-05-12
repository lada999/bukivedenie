// Lightweight fetch wrapper with timeout and visible logging
const API_BASE = (() => {
  try{
    const fromWindow = window.__API_BASE__
    if(typeof fromWindow === 'string' && fromWindow.length) return fromWindow
    const params = new URLSearchParams(location.search)
    const fromQuery = params.get('api')
    if(fromQuery) return fromQuery
    const isDevPort = location.port === '5173'
    const isLocal = ['127.0.0.1', 'localhost'].includes(location.hostname)
    return (isDevPort || isLocal) ? 'http://127.0.0.1:8000' : ''
  }catch(e){
    return ''
  }
})()

function apiPath(path){
  return `${API_BASE}${path}`
}

function appendLog(msg){
  try{
    const el = document.getElementById('logs')
    if(!el) return
    const p = document.createElement('div')
    p.textContent = msg
    p.style.padding = '6px 8px'
    p.style.borderBottom = '1px solid rgba(0,0,0,0.06)'
    p.style.fontSize = '13px'
    p.style.color = '#222'
    el.prepend(p)
  }catch(e){ /* ignore */ }
}

function logBase(){
  try{
    console.info(`API base resolved to ${API_BASE || '(same-origin)'}`)
    appendLog(`API base: ${API_BASE || '(same-origin)'}`)
  }catch(e){ /* ignore */ }
}

logBase()

export async function fetchJson(path, opts={}){
  const controller = new AbortController()
  const timeout = opts.timeout ?? 30000 // 30s default
  const timer = setTimeout(()=> controller.abort(), timeout)
  const method = (opts.method||'GET').toUpperCase()
  console.info(`${method} ${apiPath(path)} (timeout ${timeout}ms)`)
  appendLog(`${new Date().toISOString()} - ${method} ${apiPath(path)}`)
  try{
    const url = apiPath(path)
    const res = await fetch(url, { headers: { 'Accept': 'application/json' }, signal: controller.signal, ...opts })
    clearTimeout(timer)
    if(!res.ok){
      const text = await res.text().catch(()=> '')
      const msg = `HTTP ${res.status} ${res.statusText}: ${text}`
      console.error(msg)
      appendLog(`ERROR: ${msg}`)
      throw new Error(msg)
    }
    // try to parse JSON, but on failure include raw text in logs for easier debugging
    const raw = await res.text().catch(()=> '')
    try{
      const data = raw ? JSON.parse(raw) : null
      console.info(`OK ${method} ${apiPath(path)}`)
      return data
    }catch(e){
      const preview = raw ? raw.slice(0, 1000) : ''
      const msg = `Invalid JSON response${preview?`: ${preview}`:''}`
      console.error(msg)
      appendLog(`ERROR: ${msg}`)
      // also expose raw text on error object for debug inspectors
      const err = new Error('Invalid JSON response')
      err.raw = raw
      throw err
    }
  }catch(e){
    clearTimeout(timer)
    const errMsg = e.name === 'AbortError' ? 'Request timed out' : (e.message || String(e))
    console.error(`${method} ${apiPath(path)} -> ${errMsg}`)
    appendLog(`ERROR: ${method} ${apiPath(path)} -> ${errMsg}`)
    throw e
  }
}

export const api = {
  books: () => fetchJson('/api/books'),
  files: (book) => fetchJson(`/api/files?book=${encodeURIComponent(book)}`),
  fileParsed: (book, name) => fetchJson(`/api/file_parsed?book=${encodeURIComponent(book)}&name=${encodeURIComponent(name)}`),
  tokenByChapter: (book, token) => fetchJson(`/api/token_by_chapter?book=${encodeURIComponent(book)}&token=${encodeURIComponent(token)}`),
  runAnalysis: (raw) => fetchJson(`/api/run_analysis?raw=${encodeURIComponent(raw)}`),
  cloudGenerate: (book) => fetchJson(`/api/cloud_generate?book=${encodeURIComponent(book)}`),
}
