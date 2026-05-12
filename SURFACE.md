# Surface

## Backend dashboard contract

- `GET /api/book_summary?book=<book_id>` returns a cheap, compare-friendly JSON payload for dashboard-first visualizations.
- Payload includes:
  - `book`, `ready`
  - `summary` (book-level counts and chapter totals)
  - `text_index` (stable token frequency rows)
  - `fragments` (chapter-fragment rows)
  - `punctuation_timeline` (ordered punctuation counts)
