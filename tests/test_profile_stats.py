import importlib.util
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET


class StatsTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'scripts' / 'update_stats.py'
        self.assertTrue(path.exists(), 'Repository-hosted stats generator is missing')
        spec = importlib.util.spec_from_file_location('stats', path)
        self.stats = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.stats)

    def test_counts_owned_public_repositories_and_paginates(self):
        pages = {
            '/users/kpulik/repos?type=owner&per_page=100&page=1': [
                {'full_name': 'kpulik/one', 'fork': False, 'private': False, 'stargazers_count': 5, 'forks_count': 2},
                {'full_name': 'kpulik/fork', 'fork': True, 'private': False, 'stargazers_count': 99},
                {'full_name': 'kpulik/private', 'fork': False, 'private': True, 'stargazers_count': 99},
            ],
            '/users/kpulik/repos?type=owner&per_page=100&page=2': [],
            '/repos/kpulik/one/languages': {'Python': 300, 'C++': 100},
        }
        result = self.stats.collect('kpulik', pages.__getitem__)
        self.assertEqual(result, {'repos': 1, 'stars': 5, 'forks': 2, 'languages': {'Python': 300, 'C++': 100}})

    def test_cards_are_valid_accessible_svg_with_escaped_content(self):
        cards = self.stats.render('x<&', {'repos': 1, 'stars': 5, 'forks': 2, 'languages': {'C++': 75, 'A&B': 25}}, '2026-10-17')
        for content in cards.values():
            root = ET.fromstring(content)
            self.assertEqual(root.attrib['role'], 'img')
        language_text = ''.join(ET.fromstring(cards['top-languages.svg']).itertext())
        self.assertIn('75.0%', language_text)
        self.assertIn('A&B', language_text)
        self.assertIn('2026-10-17', language_text)

    def test_empty_languages_do_not_divide_by_zero(self):
        cards = self.stats.render('kpulik', {'repos': 0, 'stars': 0, 'forks': 0, 'languages': {}}, '2026-10-17')
        self.assertIn('No language data', cards['top-languages.svg'])


if __name__ == '__main__':
    unittest.main()
