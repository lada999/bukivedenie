"""
Ядро конвейера: нормализация, разбиение на абзацы/предложения, токенизация.
"""

import re
import unicodedata
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field

from .config import ExtractorConfig


@dataclass
class Token:
    """Токен с метаданными."""
    text: str
    text_lower: str
    start_offset: int
    end_offset: int
    token_type: str  # word, number, punct, symbol, abbrev, roman, url, email
    lemma: Optional[str] = None
    is_dialog: bool = False
    contains_quote: bool = False


@dataclass
class Sentence:
    """Предложение с метаданными."""
    text: str
    start_offset: int
    end_offset: int
    tokens: List[Token] = field(default_factory=list)
    is_dialog: bool = False
    contains_quote: bool = False
    chapter_idx: int = 0


@dataclass
class Paragraph:
    """Абзац с метаданными."""
    text: str
    start_offset: int
    end_offset: int
    sentences: List[Sentence] = field(default_factory=list)
    is_dialog: bool = False
    chapter_idx: int = 0


@dataclass
class Chapter:
    """Глава."""
    title: str
    start_offset: int
    end_offset: int
    paragraphs: List[Paragraph] = field(default_factory=list)
    chapter_idx: int = 0


class TextPipeline:
    """
    Детерминированный конвейер обработки текста.
    """
    
    # Паттерны для токенизации
    URL_PATTERN = re.compile(
        r'https?://\S+|www\.\S+',
        re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    NUMBER_PATTERN = re.compile(
        r'\d+(?:[.,]\d+)*'
    )
    WORD_PATTERN = re.compile(
        r'\w+',
        re.UNICODE
    )
    
    # Аббревиатуры, не являющиеся концом предложения
    ABBREV_EXCEPTIONS = {
        'ru': {'г', 'гр', 'т', 'тов', 'ул', 'пр', 'просп', 'пер', 'им', 'о', 'обл', 
               'край', 'респ', 'авто', 'инж', 'проф', 'др', 'мл', 'млад', 'ст', 
               'стар', 'нац', 'мин', 'гос', 'фед', 'рос', 'ссср', 'сша', 'оон',
               'т.е', 'т.д', 'и.т.д', 'и.т.п', 'напр', 'см', 'см.т'},
        'en': {'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'i.e', 
               'e.g', 'cf', 'al', 'fig', 'figs', 'ed', 'eds', 'rev', 'vol', 'nos',
               'approx', 'dept', 'univ', 'assn', 'bros', 'co', 'corp', 'inc', 'ltd'}
    }
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self._lemmatizer = None
        self._init_lemmatizer()
    
    def _init_lemmatizer(self):
        """Инициализация лемматизатора (с graceful fallback)."""
        if not self.config.use_lemmas:
            return
        
        if self.config.lang == "ru":
            try:
                import pymorphy2
                self._lemmatizer = pymorphy2.MorphAnalyzer()
            except (ImportError, AttributeError, Exception) as e:
                if self.config.verbose:
                    print(f"[WARN] pymorphy2 недоступен ({e}), отключаю лемматизацию")
                self.config.use_lemmas = False
                self._lemmatizer = None
    
    def normalize(self, text: str) -> str:
        """
        Нормализация текста:
        - NFC Unicode
        - CRLF -> LF
        - Унификация кавычек, тире, многоточий
        - Нормализация пробелов
        - Удаление управляющих символов
        """
        # NFC нормализация
        text = unicodedata.normalize('NFC', text)
        
        # CRLF -> LF
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Replace non-breaking / unusual spaces
        for sp in ('\u00a0','\u2007','\u202f'):
            text = text.replace(sp, ' ')
        
        # Унификация кавычек
        quote_map = {
            '«': '"', '»': '"', '„': '"', '“': '"', '”': '"', "'": "'"
        }
        for old, new in quote_map.items():
            text = text.replace(old, new)
        
        # Унификация тире и дефисов
        text = text.replace('–', '—').replace('-', '‑')
        
        # Унификация многоточий
        text = re.sub(r'\.{3,}', '…', text)
        
        # Нормализация пробелов (но сохраняем структуру абзацев)
        lines = text.split('\n')
        normalized_lines = []
        for line in lines:
            # Убираем лишние пробелы внутри строки
            line = re.sub(r'[ \t]+', ' ', line).strip()
            normalized_lines.append(line)
        text = '\n'.join(normalized_lines)
        
        # Удаление управляющих символов (кроме \n, \t)
        text = ''.join(
            ch for ch in text 
            if unicodedata.category(ch)[0] != 'C' or ch in '\n\t'
        )
        
        return text
    
    def detect_chapters(
        self, 
        text: str, 
        pattern: Optional[str] = None
    ) -> List[Tuple[int, int, str]]:
        """
        Детекция глав. Возвращает список (start_offset, end_offset, title).

        Теперь заголовок ограничен только маркером:
        - римская цифра (I., II., III и т.п.),
        - или слово 'Глава' (включая возможный номер),
        - аналогично для английского 'Chapter'.

        Это предотвращает захват нескольких строк после метки.
        """
        if pattern:
            chapter_regex = re.compile(pattern, re.MULTILINE)
            token_re = re.compile(pattern, re.MULTILINE)
        else:
            if self.config.lang == "ru":
                # базовые маркеры: Глава, Часть, Книга с опциональным номером
                base = r'(?:Глава\s*(?:\d+|[IVXLCM]+)?|Часть\s*\d+|Книга\s*\d+)'
                # римская цифра (только если она отдельный токен: I, II, IV. и т.п.)
                roman_line = r'[IVXLCDM]{1,6}\.?(?=\s|$)'
                chapter_regex = re.compile(r'^\s*(?:' + base + r'|' + roman_line + r')', re.MULTILINE | re.IGNORECASE)
                # token_re — выдирает только маркер (без остального содержимого строки)
                token_re = re.compile(r'^\s*(?:Глава\s*(?:\d+|[IVXLCDM]+)?|Часть\s*\d+|Книга\s*\d+|' + roman_line + r')', re.IGNORECASE)
            else:
                base = r'(?:Chapter\s*(?:\d+|[IVXLCM]+)?|Part\s*\d+|Book\s*\d+)'
                roman_line = r'[IVXLCDM]{1,6}\.?(?=\s|$)'
                chapter_regex = re.compile(r'^\s*(?:' + base + r'|' + roman_line + r')', re.MULTILINE | re.IGNORECASE)
                token_re = re.compile(r'^\s*(?:Chapter\s*(?:\d+|[IVXLCDM]+)?|Part\s*\d+|Book\s*\d+|' + roman_line + r')', re.IGNORECASE)
        
        chapters = []
        matches = list(chapter_regex.finditer(text))
        
        if not matches:
            return [(0, len(text), "Весь текст")]
        
        for i, match in enumerate(matches):
            start = match.start()
            # извлекаем первую непустую строку, где расположен матч
            # (иногда заголовок и номер могут быть на нескольких строках)
            line_end = text.find('\n', start)
            if line_end == -1:
                line_end = len(text)
            line = text[start:line_end].strip()

            # Попробуем извлечь компактный маркер (римская цифра или слово 'Глава')
            title = None
            try:
                if 'token_re' in locals() and token_re:
                    m = token_re.match(line)
                    if m:
                        title = m.group(0).strip()
            except Exception:
                title = None

            # Если маркер не найден, используем всю строку (но урежем до 80 символов)
            if not title:
                short = re.sub(r'\s+', ' ', line)
                title = short if len(short) <= 80 else (short[:77] + '...')

            # Если пользователь передал кастомный pattern и в нём есть именованная группа 'title',
            # попробуем достать её содержимое (приоритет)
            if pattern:
                try:
                    m_full = match
                    if 'title' in m_full.groupdict():
                        g = m_full.group('title')
                        if g:
                            title = g.strip()
                except Exception:
                    pass

            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            # Гарантируем, что title не пуст
            if not title:
                title = f"Глава {i+1}"
            chapters.append((start, end, title))

        # Постобработка: объединяем заведомо крошечные главы (false positives), т.к.
        # паттерн может ловить римские цифры и прочие маркеры, встречающиеся внутри текста
        MIN_CHARS = 200
        if len(chapters) > 1:
            merged = []
            pending = None
            for (s, e, t) in chapters:
                size = e - s
                if size < MIN_CHARS:
                    # too small — merge with neighbor
                    if pending is None and not merged:
                        # no previous merged item: set pending to merge into next
                        pending = (s, e, t)
                        continue
                    elif pending is not None and not merged:
                        # we have pending but still no merged items -> extend pending
                        pending = (pending[0], e, pending[2])
                        continue
                    else:
                        # merge into previous merged item
                        ps, pe, pt = merged[-1]
                        merged[-1] = (ps, e, pt)
                        continue
                else:
                    if pending is not None and not merged:
                        # merge pending into this chapter
                        ns, ne, nt = (pending[0], e, t)
                        merged.append((ns, ne, t))
                        pending = None
                    else:
                        merged.append((s, e, t))
            # if pending remains and merged non-empty, merge it into first merged
            if pending is not None and merged:
                fs, fe, ft = merged[0]
                merged[0] = (pending[0], fe, ft)
                pending = None

            # Filter out any invalid ranges
            merged = [m for m in merged if m[1] > m[0]]
            if self.config.verbose:
                print(f"[DEBUG] detect_chapters: {len(chapters)} matches -> {len(merged)} after merging small ones (MIN_CHARS={MIN_CHARS})")
            return merged

        return chapters
    
    def split_paragraphs(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Разбиение на абзацы.
        Возвращает список (start_offset, end_offset, text).
        """
        paragraphs = []
        # 2+ перевода строки = разделитель абзацев
        para_pattern = re.compile(r'\n\s*\n')
        
        start = 0
        for match in para_pattern.finditer(text):
            para_text = text[start:match.start()].strip()
            if para_text:
                paragraphs.append((start, match.start(), para_text))
            start = match.end()
        
        # Последний абзац
        remaining = text[start:].strip()
        if remaining:
            paragraphs.append((start, len(text), remaining))
        
        return paragraphs
    
    def split_sentences(
        self, 
        text: str, 
        start_offset: int = 0
    ) -> List[Tuple[int, int, str]]:
        """
        Разбиение на предложения.
        Использует razdel при доступности; fallback — простая эвристика.
        Возвращает список (start_offset, end_offset, text).
        """
        try:
            from razdel import sentenize
        except Exception:
            sentenize = None

        sentences = []

        if sentenize is not None:
            # razdel возвращает объекты с start, stop, text
            for s in sentenize(text):
                sentences.append((start_offset + s.start, start_offset + s.stop, s.text))
            if sentences:
                return sentences

        # Fallback: простое разбиение по [.!?…]+
        simple_pattern = re.compile(r'([.!?…]+)')
        parts = simple_pattern.split(text)

        current_start = start_offset
        current_text = ""

        for i, part in enumerate(parts):
            if not part:
                continue

            if i % 2 == 0:  # Текст
                current_text += part
            else:  # Знак конца предложения
                current_text += part
                sent_text = current_text.strip()
                if sent_text:
                    sent_end = current_start + len(current_text)
                    sentences.append((current_start, sent_end, sent_text))
                current_text = ""
                current_start = sent_end

        # Остаток
        if current_text.strip():
            sentences.append((
                current_start, 
                current_start + len(current_text), 
                current_text.strip()
            ))

        return sentences if sentences else [(start_offset, start_offset + len(text), text)]
    
    def _classify_token(self, text: str) -> str:
        """Классификация токена."""
        if self.URL_PATTERN.match(text):
            return 'url'
        if self.EMAIL_PATTERN.match(text):
            return 'email'
        if self.NUMBER_PATTERN.match(text):
            return 'number'
        if self.WORD_PATTERN.match(text):
            # Проверка на римские цифры
            if re.match(r'^[IVXLCM]+$', text, re.IGNORECASE):
                return 'roman'
            # Проверка на аббревиатуру (все заглавные)
            if text.isupper() and len(text) >= 2:
                return 'abbrev'
            return 'word'
        return 'punct'
    
    def tokenize(
        self, 
        text: str, 
        start_offset: int = 0
    ) -> List[Token]:
        """
        Токенизация текста.
        """
        tokens = []
        
        # Простая токенизация по границам слов/чисел/знаков
        pattern = re.compile(
            r'(\w+|[^\w\s])',
            re.UNICODE
        )
        
        for match in pattern.finditer(text):
            token_text = match.group(0)
            token_type = self._classify_token(token_text)
            
            # Лемматизация для слов
            lemma = None
            if token_type == 'word' and self._lemmatizer and self.config.use_lemmas:
                try:
                    parsed = self._lemmatizer.parse(token_text)[0]
                    lemma = parsed.normal_form
                except Exception:
                    lemma = token_text.lower()
            
            token = Token(
                text=token_text,
                text_lower=token_text.lower(),
                start_offset=start_offset + match.start(),
                end_offset=start_offset + match.end(),
                token_type=token_type,
                lemma=lemma
            )
            tokens.append(token)
        
        return tokens
    
    def detect_dialog(self, text: str) -> bool:
        """
        Детекция диалога/прямой речи.
        """
        # Начинается с тире или кавычки
        stripped = text.strip()
        if stripped.startswith('—') or stripped.startswith('-'):
            return True
        if stripped.startswith('"') or stripped.startswith('"'):
            return True
        return False
    
    def has_quotes(self, text: str) -> bool:
        """Проверка наличия кавычек."""
        return '"' in text or '"' in text or "'" in text
    
    def process(
        self, 
        raw_text: str, 
        book_id: str
    ) -> Dict[str, Any]:
        """
        Полный конвейер обработки текста.
        Возвращает структурированные данные.
        """
        # Нормализация
        canonical_text = self.normalize(raw_text)
        
        # Детекция глав
        chapter_ranges = self.detect_chapters(
            canonical_text, 
            self.config.chapter_pattern
        )
        
        chapters: List[Chapter] = []
        all_sentences: List[Sentence] = []
        all_paragraphs: List[Paragraph] = []
        
        for ch_idx, (ch_start, ch_end, ch_title) in enumerate(chapter_ranges):
            chapter_text = canonical_text[ch_start:ch_end]
            
            chapter = Chapter(
                title=ch_title,
                start_offset=ch_start,
                end_offset=ch_end,
                chapter_idx=ch_idx
            )
            
            # Абзацы внутри главы
            para_ranges = self.split_paragraphs(chapter_text)
            
            for p_start_rel, p_end_rel, p_text in para_ranges:
                p_start = ch_start + p_start_rel
                p_end = ch_start + p_end_rel
                
                paragraph = Paragraph(
                    text=p_text,
                    start_offset=p_start,
                    end_offset=p_end,
                    is_dialog=self.detect_dialog(p_text),
                    chapter_idx=ch_idx
                )
                
                # Предложения внутри абзаца
                sent_ranges = self.split_sentences(p_text, p_start)
                
                for s_start, s_end, s_text in sent_ranges:
                    sentence = Sentence(
                        text=s_text,
                        start_offset=s_start,
                        end_offset=s_end,
                        is_dialog=self.detect_dialog(s_text),
                        contains_quote=self.has_quotes(s_text),
                        chapter_idx=ch_idx,
                        tokens=self.tokenize(s_text, s_start)
                    )
                    paragraph.sentences.append(sentence)
                    all_sentences.append(sentence)
                
                chapter.paragraphs.append(paragraph)
                all_paragraphs.append(paragraph)
            
            chapters.append(chapter)
        
        return {
            'book_id': book_id,
            'raw_text': raw_text,
            'canonical_text': canonical_text,
            'chapters': chapters,
            'paragraphs': all_paragraphs,
            'sentences': all_sentences,
            'total_chars': len(canonical_text),
            'total_paragraphs': len(all_paragraphs),
            'total_sentences': len(all_sentences),
        }
