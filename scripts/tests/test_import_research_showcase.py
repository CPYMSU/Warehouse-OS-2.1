import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    'showcase_import', Path(__file__).resolve().parents[1] / 'import_research_showcase.py'
)
showcase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(showcase)


class ShowcaseImportTests(unittest.TestCase):
    def setUp(self):
        self.edition = showcase.Edition('http://127.0.0.1:8000/')

    def test_new_research_pages_and_paper_are_selected(self):
        catalog = {(group, path) for group, path, *_ in showcase.DOCUMENTS}
        self.assertIn(('mk78', 'mk78/index.html'), catalog)
        self.assertIn(('mk79', 'mk79/index.html'), catalog)
        self.assertIn(('mk79', 'papers/mk79-manuscript.pdf'), catalog)
        self.assertIn(('mk73', 'papers/mk73-dissertation.pdf'), catalog)
        self.assertIn(('mk77', 'papers/mk77-manuscript.pdf'), catalog)
        self.assertEqual(self.edition.resolve('/mk79/index.html#model', 'mk78/index.html'),
                         ('mk79/index.html', 'model'))
        with self.assertRaises(ValueError):
            self.edition.resolve('/%2e%2e/private.txt', 'mk79/index.html')

    def test_internal_links_and_local_assets_are_imported(self):
        self.edition.originals['mk79/chart.svg'] = b'<svg></svg>'
        page = showcase.Page(self.edition, 'mk79/index.html')
        page.feed('<a href="/mk78/index.html#example">go</a><img src="chart.svg">')
        output = ''.join(page.output)
        self.assertIn('data-showcase-path="mk78/index.html#example"', output)
        self.assertIn('data:image/svg+xml;base64,', output)
        self.assertIn('mk78/index.html', self.edition.pending)


if __name__ == '__main__':
    unittest.main()
