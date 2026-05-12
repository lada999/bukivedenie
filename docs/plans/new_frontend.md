Новый план фронтенда: путь простоты (без фреймворков)
=====================================================

Кратко
------
Мы упрощаем фронтенд до ванильных ES‑модулей с быстрым dev‑циклом, без React/SPA‑фреймворков и без самодельных dev‑tools. Используем готовые, проверенные решения там, где это уместно: Rollup (watch+serve) или простой CDN‑режим для сборки/разработки, ECharts как основной декларативный движок для диаграмм, Cytoscape.js для графов, wordcloud2.js или `echarts-wordcloud` для облака слов, лёгкую CSS‑библиотеку для базовой типографики. Главная метафора интерфейса — интерактивный атлас книги, а не набор разрозненных страниц. Путь простой: сначала быстрый MVP, потом расширение.

Главные принципы (в духе простоты)
- Не изобретать заново: не пишем собственные dev‑панели, роутеры‑монстры и компоненты‑фреймворки.
- Меньше зависимостей — быстрее «холодный старт» и меньше поддержки.
- Backend уже парсит данные (/api/file_parsed) — на фронте только визуализируем и управляем запросами.
- Mobile‑first: интерфейс удобен на телефоне; для разработки — стандартные браузерные DevTools и live‑reload от rollup/browser-sync.

Ключевые решения
----------------
1) Dev‑сервер и сборка: Rollup (vanilla) или простой статический режим
   - Используем rollup + rollup-plugin-serve + rollup-plugin-livereload для watch/serve и live‑reload.
   - В качестве альтернативы можно работать через browser-sync, который проксирует backend и следит за изменениями в src/web_view.
   - Для окружений без Node используйте CDN‑index.html (static), который подключает библиотеки напрямую.

2) Язык: обычные ES‑модули (без фреймворков)
   - Опционально можно будет перейти на TypeScript (vanilla‑ts), но изначально — чистый JS.

3) Визуализации (готовые библиотеки)
    - Основные графики: ECharts (bar, line, histogram, heatmap, sunburst, treemap, graph, sankey и т.д.).
    - Дополнительные declarative-спеки: Vega‑Lite + vega‑embed там, где спецификация короче или удобнее для простых статических графиков.
    - Сеть персонажей / граф связей: Cytoscape.js + layout-плагины (co‑occurrence, zoom/pan, подсветка, кластеризация).
    - Облако слов: `echarts-wordcloud` как первый выбор; `wordcloud2.js` оставляем как fallback, если нужен отдельный canvas-рендер.
    - D3 НЕ подключаем по умолчанию (добавим только при реальной необходимости low-level кастомизации).
    - Атлас книги: отдельный линейный виджет с главами, репликами, пунктуацией, мотивами и аномалиями по ходу текста.
    - Первая фаза: `Book Atlas`, top words, punctuation timeline, text viewer.

4) UI/стили
   - Pico.css (CDN) — минимальный базовый стиль без сборки и классовых фреймворков.
   - Свой небольшой CSS (layout.css, mobile.css) — только точечные правки.

5) Dev‑tools
   - Не реализуем свои. Используем Rollup watch + live‑reload или browser-sync и стандартные DevTools/remote debugging.

6) Интерактивность
   - hover показывает абсолюты;
   - click фиксирует выбранный объект и синхронизирует все виджеты;
   - double click ведёт к текстовому фрагменту;
   - brush по оси текста фильтрует остальные панели.

7) Завиcимость от backend
   - фронту нужны уже собранные payload'ы для atlas, tokens, motifs, dialogues, punctuation timeline и compare mode;
   - на каждый hover не должно быть сетевого пересчёта сырого текста;
   - сравнение книг и фрагментов должно приходить готовым JSON.
   - если backend не готов, UI должен показывать минимальный working set, а не блокироваться.

Состав библиотек (точный)
-------------------------
Устанавливаем через npm в проекте frontend/:
- rollup — dev‑watch/serve и сборка
- echarts, echarts-wordcloud — основной декларативный набор визуализаций
- cytoscape, cytoscape-dagre, cytoscape-fcose — графы и сетевые диаграммы
- vega, vega‑lite, vega‑embed — дополнительные визуализации там, где удобнее оставить spec-first подход
- wordcloud — wordcloud2.js для fallback-облака слов
- (без axios — используем fetch; без D3 — по умолчанию не тащим)
- (опционально позже) arquero — если понадобится более мощная табличная обработка в браузере

CDN‑альтернативы (для нулевого режима без node)
  - ECharts: https://cdn.jsdelivr.net/npm/echarts@5
  - echarts-wordcloud: https://cdn.jsdelivr.net/npm/echarts-wordcloud
  - Cytoscape: https://cdn.jsdelivr.net/npm/cytoscape@3
  - Vega: https://cdn.jsdelivr.net/npm/vega@5
  - Vega‑Lite: https://cdn.jsdelivr.net/npm/vega-lite@5
  - vega‑embed: https://cdn.jsdelivr.net/npm/vega-embed@6
  - wordcloud2.js: https://cdn.jsdelivr.net/npm/wordcloud
- Pico.css: https://unpkg.com/@picocss/pico@1.*/css/pico.min.css

Архитектура файлов
------------------
frontend/
  index.html           # точка входа, подключает /src/main.js, Pico.css по CDN
  package.json
  rollup.config.js     # конфиг rollup (serve + livereload для dev)
  src/
    main.js            # инициализация, простой hash‑router, монтирование view
    api.js             # fetchJson(path, opts): минимальная обёртка над fetch
    router.js          # очень простой hash‑router (#/books, #/book/:id, ...)
    ui/
      topbar.js        # верхняя панель навигации
    views/
      booksList.js     # список книг (GET /api/books)
      bookOverview.js  # обзор книги (metadata, быстрые ссылки)
      filesList.js     # файлы книги (GET /api/files)
      fileViewer.js    # просмотр CSV/JSON/JSONL (исп. /api/file_parsed)
       tokensChart.js   # топ‑N токенов (ECharts bar)
       wordCloud.js     # облако слов (echarts-wordcloud)
       networkGraph.js  # сеть персонажей (Cytoscape.js)
       sentimentChart.js # тональность по главам (ECharts line)
    viz/
      vegaHelper.js    # renderSpec(el, spec, options) через vega‑embed
      networkHelper.js # createNetwork(el, nodes, edges)
    styles/
      base.css
      layout.css
      mobile.css

Навигация и дизайн (mobile‑first)
---------------------------------
- Простой topbar: назад, заголовок, ссылка «Книги».
- Hash‑роутинг:
  - #/books — список книг
  - #/book/:id — обзор книги (краткая статистика, действия: Tokens, WordCloud, Network, Sentiment, Files)
  - #/book/:id/viz/tokens — бар‑чарт частот
  - #/book/:id/viz/wordcloud — облако слов
  - #/book/:id/viz/network — сеть персонажей
  - #/book/:id/viz/sentiment — линия тональностей по главах
  - #/book/:id/files — список файлов
  - #/book/:id/file/:name — просмотр файла
- На мобильном: вертикальные списки, крупные тапы, минимализм интерфейса, упор на содержимое.

Связь с backend (что используем)
--------------------------------
- GET /api/books — список книг (картинки/кнопки перехода)
- GET /api/files?book= — список файлов книги
- GET /api/file_parsed?book=&name= — безопасный просмотр для CSV/JSON/JSONL
- GET /api/token_by_chapter?book=&token= — данные для распределения по главам
- GET /api/figures?book= и /api/figure_download — если нужны готовые изображения
- GET /api/run_analysis?raw= — запуск анализа (кнопка на Books/Overview)
- GET /api/cloud_generate?book= — генерация облака (кнопка на Overview)

Dev proxy / proxy-сервер
------------------------
При использовании rollup-plugin-serve или browser-sync можно настроить проксирование /api → http://127.0.0.1:8000. scripts/dev.sh и scripts/dev_rollup.sh ожидают, что frontend-serve будет слушать порт 5173, либо что browser-sync будет проксировать backend и подавать статику.


Производственный режим
----------------------
Два варианта:
1) Копирование dist в web_view (по умолчанию)
   - npm run build → frontend/dist → копируем в src/web_view/
   - webapp.py продолжит отдавать index.html и статику из WEB_ROOT (src/web_view)

2) Перенастроить WEB_ROOT на ../frontend/dist
   - Изменить WEB_ROOT в src/webapp.py, чтобы раздавать из frontend/dist напрямую.
   - Плюс: не копируем файлы. Минус: зависимость от расположения каталога.

Makefile: задачи
----------------
frontend-install:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build
	rm -rf src/web_view/* || true
	cp -r frontend/dist/* src/web_view/

frontend-deploy: frontend-build

Шаги внедрения
---------------
1) Бэкап текущего фронта
   mkdir -p archives
   tar -czf archives/web_view-backup-$(date +%Y%m%d-%H%M%S).tar.gz src/web_view

2) Scaffold минимального фронта (Rollup / vanilla)
   Создайте минимальную структуру frontend/ или используйте готовый шаблон rollup+vanilla.
   Вручную:
     mkdir frontend && cd frontend
     npm init -y
     npm install --save vega vega-lite vega-embed vis-network wordcloud
     npm install --save-dev rollup @rollup/plugin-node-resolve @rollup/plugin-commonjs rollup-plugin-serve rollup-plugin-livereload

3) Настройка proxy (через rollup-plugin-serve или browser-sync) и базовых скриптов (package.json)
   - dev, build, preview

4) Реализация базовой навигации и страниц
   - #/books, #/book/:id, #/book/:id/files, #/book/:id/file/:name
   - Подключить Pico.css по CDN в index.html

5) Визуализации (минимальный набор)
    - bookAtlas.js (ECharts custom/heatmap: линейная карта книги по ходу текста)
    - tokensChart.js (ECharts bar: топ‑N из tokens.csv)
    - wordCloud.js (echarts-wordcloud: из tokens.csv)
    - networkGraph.js (Cytoscape.js: из cooccurrence_edges.csv)
    - sentimentChart.js (ECharts line: из sentiment_by_chapter.csv)
    - phase2 widgets only after phase1 is stable.

6) Сборка и деплой
   - npm run build
   - копирование dist/* в src/web_view/ (или смена WEB_ROOT)

7) Документация и поддержка
   - Короткий README в frontend/ (команды dev/build, структура модулей)
   - Поддерживаем минимальный код: без самописных тулбаров и тяжёлых зависимостей

Почему это оптимально
---------------------
- Соответствует требованию «современно, но просто»: HMR и сборка есть, но без фреймворков и лишних слоёв.
- Использует готовые, лёгкие библиотеки для сложных задач визуализации (диаграммы/графы/облака), избегая «изобретения велосипеда».
- Лёгкий вход для агента/разработчика: простая файловая структура, минимум конфигов, возобновляемость по README/Makefile.

Альтернативный нулевой режим (без node) — справка
-----------------------------------------------
Если принципиально нужен «без node» режим:
- index.html + CDN (vega, vega‑lite, vega‑embed, vis‑network, wordcloud, Pico.css)
- ES‑модули в src/web_view/static/js/* (type="module")
- Локальный сервер: python -m http.server (без HMR)
- Минусы: нет proxy/HMR, сложнее масштабировать. Рекомендуется только при жёстких ограничениях окружения.

Оценка усилий
-------------
- Бэкап и scaffold: 30–40 минут
- База навигации и страницы: 1–2 часа
- 3–4 ключевые визуализации: 2–4 часа
- Сборка/деплой/полировка: 30–60 минут
Итого: ~4–8 часов до удобного MVP.
