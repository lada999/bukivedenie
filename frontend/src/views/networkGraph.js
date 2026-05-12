import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import { api } from '../api.js'

export async function viewNetwork(book){
  const el = document.getElementById('view')
  if(!el){
    console.error('view mount not found in viewNetwork')
    return
  }
  el.innerHTML = `<h2>${book}: Character Network</h2><p>Загружаю…</p>`
  const files = await api.files(book).then(r=>r.files||[])
  const name = 'cooccurrence_edges.csv'
  if(!files.includes(name)){
    el.innerHTML = `<h2>${book}: Character Network</h2><p>Нет данных</p>`
    return
  }
  const { type, headers=[], rows=[] } = await api.fileParsed(book, name)
  if(type !== 'csv' || !rows.length){
    el.innerHTML = `<h2>${book}: Character Network</h2><p>Нет данных</p>`
    return
  }
  // headers: ['source','source_lower','target','target_lower','weight', ...]
  const nodesMap = new Map()
  const edges = []
  for(const r of rows){
    const s = r[0], t = r[2], w = +r[4] || 1
    if(!nodesMap.has(s)) nodesMap.set(s, { id: s, label: s })
    if(!nodesMap.has(t)) nodesMap.set(t, { id: t, label: t })
    edges.push({ from: s, to: t, value: w })
  }
  el.innerHTML = `<div id="net" style="width:100%; min-height:480px;"></div>`
  const container = document.getElementById('net')
  try{
    const data = { nodes: new DataSet(Array.from(nodesMap.values())), edges: new DataSet(edges) }
    const options = { physics: { stabilization: true }, edges: { smooth: true }, interaction: { hover: true } }
    new Network(container, data, options)
  }catch(e){
    console.error('Error initializing vis-network', e)
    container.innerHTML = '<p>vis-network initialization error</p>'
  }
}
