// Minimal vanilla entry: hash router + topbar + initial view
import { initRouter } from './router.js'
import { renderTopbar } from './ui/topbar.js'

function mount() {
  let app = document.getElementById('app')
  if(!app){
    // If #app missing (different index.html or server), create it to avoid crashing
    console.warn('No #app element found — creating one dynamically')
    app = document.createElement('div')
    app.id = 'app'
    // Prefer to prepend so it's before any overlay buttons
    document.body && document.body.prepend ? document.body.prepend(app) : document.documentElement.appendChild(app)
  }

  try{
    window.__APP_READY__ = false
    app.innerHTML = `
      <header class="container">
        <div id="topbar"></div>
      </header>
      <main class="container" id="view"></main>
      <aside id="logs" style="position:fixed; left:8px; bottom:8px; width:320px; max-height:40vh; overflow:auto; background:rgba(255,255,255,0.95); border:1px solid rgba(0,0,0,0.06); box-shadow:0 6px 18px rgba(0,0,0,0.06); padding:8px; display:none; z-index:99998; font-size:13px;"></aside>
    `
  }catch(e){
    console.error('Failed to set app.innerHTML', e)
  }

  window.addEventListener('error', event => {
    try{
      const logs = document.getElementById('logs')
      if(logs){
        const p = document.createElement('div')
        p.textContent = `ERROR: ${event.message || event.error?.message || 'unknown error'}`
        p.style.padding = '6px 8px'
        p.style.borderBottom = '1px solid rgba(0,0,0,0.06)'
        logs.prepend(p)
      }
    }catch(e){ /* ignore */ }
  })

  window.addEventListener('unhandledrejection', event => {
    try{
      const logs = document.getElementById('logs')
      if(logs){
        const p = document.createElement('div')
        p.textContent = `PROMISE: ${event.reason?.message || event.reason || 'unhandled rejection'}`
        p.style.padding = '6px 8px'
        p.style.borderBottom = '1px solid rgba(0,0,0,0.06)'
        logs.prepend(p)
      }
    }catch(e){ /* ignore */ }
  })

  try{
    const topbarEl = document.getElementById('topbar')
    if(topbarEl){
      renderTopbar(topbarEl)
    }else{
      console.warn('topbar element not found')
    }
  }catch(e){
    console.error('renderTopbar failed', e)
  }

  try{
    initRouter()
  }catch(e){
    console.error('initRouter failed', e)
  }

  window.__APP_READY__ = true
}

if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', mount)
}else{
  mount()
}
