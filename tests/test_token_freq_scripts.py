import unittest
from pathlib import Path
import csv

class TestTokenFreqByChapterFiles(unittest.TestCase):
    OUTPUTS = Path('outputs')

    def test_token_freq_files_exist_and_valid(self):
        """For each outputs/<book> that has chapters_summary.json, token_freq_by_chapter.csv should exist and be CSV with counts."""
        books = []
        for p in sorted(self.OUTPUTS.iterdir()):
            if not p.is_dir():
                continue
            if (p / 'chapters_summary.json').exists():
                books.append(p)
        # require at least one
        self.assertTrue(len(books) > 0, 'No books with chapters_summary.json found in outputs')
        for p in books:
            csvf = p / 'token_freq_by_chapter.csv'
            self.assertTrue(csvf.exists(), f'{csvf} missing for {p.name}')
            # check header and at least one data row
            with csvf.open('r', encoding='utf-8', newline='') as fh:
                reader = csv.reader(fh)
                header = next(reader, None)
                self.assertIsNotNone(header)
                self.assertIn('token', header)
                # peek at first data row
                row = next(reader, None)
                self.assertIsNotNone(row, f'No data rows in {csvf}')
                # expect count in 4th column
                if len(row) >= 4:
                    try:
                        cnt = int(row[3])
                    except Exception as e:
                        self.fail(f'Count column is not int in {csvf}: {e}')

if __name__ == '__main__':
    unittest.main()
