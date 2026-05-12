import { api } from '../api.js'
import { renderSpec } from '../viz/vegaHelper.js'

export async function viewHeatmap(book){
  const el = document.getElementById('view')
  if(!el){
    console.error('view mount not found in viewHeatmap')
    return
  }
  el.innerHTML = `<h2>${book}: Heatmap (top tokens × главы)</h2><p>Загружаю…</p>`
  const { files } = await api.files(book)
  const name = files.includes('tokens.csv') ? 'tokens.csv' : (files.find(f=>f.endsWith('_tokens.csv')) || 'tokens.csv')
  const { type, rows=[] } = await api.fileParsed(book, name)
  if(type !== 'csv' || !rows.length){
    el.innerHTML = `<h2>${book}: Heatmap</h2><p>Нет данных tokens.csv</p>`
    return
  }
  const topN = 15
  const tokens = rows.slice(0, topN).map(r=>r[0])
  el.innerHTML = `<h2>${book}: Heatmap</h2><p>Собираю распределения по главам для ${tokens.length} токенов…</p><div id="hm"></div>`
  const matrix = []
  for(const t of tokens){
    try{
      const r = await api.tokenByChapter(book, t)
      const counts = r.counts || []
      for(const c of counts){
        matrix.push({ token: t, chapter: c.title || String(c.chapter_idx), count: +c.count })
      }
    }catch(e){ console.warn('tokenByChapter fail', t, e) }
  }
  if(!matrix.length){
    document.getElementById('hm').innerHTML = '<p>Нет данных для теплокарты</p>'
    return
  }
  const spec = {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'Token × Chapter heatmap',
    data: { values: matrix },
    mark: 'rect',
    encoding: {
      x: { field: 'chapter', type: 'ordinal', sort: 'ascending' },
      y: { field: 'token', type: 'nominal', sort: 'descending' },
      color: { field: 'count', type: 'quantitative' },
      tooltip: [ {field:'token'},{field:'chapter'},{field:'count','type':'quantitative'} ]
    },
    width: 'container',
    height: { step: 18 }
  }
  await renderSpec(document.getElementById('hm'), spec)
}
