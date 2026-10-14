import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from highway_contracts.crawler import Fetcher, Links, canonical, crawl
import urllib.error
from highway_contracts.store import Store


class FakePage:
    def extract_text(self):
        return 'Environmental vegetation maintenance and roadside mowing services.'


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    @patch('highway_contracts.store.PdfReader')
    def test_versions_idempotence_and_latest_search(self, reader):
        reader.return_value.pages = [FakePage()]
        args = ('https://agency.gov/bid.pdf', 'agency', 'PA', 'Mowing', 'https://agency.gov/bids')
        self.assertTrue(self.store.index(b'%PDF-v1', *args))
        self.assertFalse(self.store.index(b'%PDF-v1', *args))
        self.assertTrue(self.store.index(b'%PDF-v2', *args))
        self.assertEqual(2, self.store.db.execute('SELECT COUNT(*) FROM documents').fetchone()[0])
        results = self.store.search('environment*', 'PA')
        self.assertEqual(1, len(results))
        self.assertEqual(1, results[0]['page'])
        self.assertEqual([], self.store.search('mowing', 'UT'))

    @patch('highway_contracts.crawler.Fetcher.get')
    @patch('highway_contracts.store.PdfReader')
    def test_discovery_limits_and_offsite_exclusion(self, reader, fetch):
        reader.return_value.pages = [FakePage()]
        fetch.side_effect = [(b'<a href="/mowing.pdf">Mowing</a><a href="https://other.gov/bid.pdf">Mowing</a>', 'text/html'),
                             (b'%PDF-test', 'application/pdf')]
        source = {'id':'test','name':'Agency','state':'PA','start_urls':['https://agency.gov/bids'],
                  'allowed_hosts':['agency.gov'],'follow_terms':['mowing'],'max_depth':2}
        report = crawl(source, self.store, 2)
        self.assertEqual(1, report['indexed'])
        self.assertEqual(2, fetch.call_count)
        self.assertFalse(report['errors'])

    @patch('highway_contracts.crawler.Fetcher.get', side_effect=PermissionError('robots denied'))
    def test_failure_is_reported(self, fetch):
        source = {'id':'test','name':'Agency','state':'PA','start_urls':['https://agency.gov/'],
                  'allowed_hosts':['agency.gov'],'follow_terms':['mowing']}
        report = crawl(source, self.store, 1)
        self.assertTrue(report['needs_adapter_review'])
        self.assertEqual(1, len(report['errors']))

    def test_url_normalization_and_links(self):
        self.assertIsNone(canonical('javascript:alert(1)'))
        self.assertIsNone(canonical('https://user:secret@agency.gov/'))
        self.assertEqual('https://agency.gov/bid?id=2', canonical('https://AGENCY.gov/bid?id=2#page=1'))
        parser = Links()
        parser.feed('<a href="bid.pdf">Roadside <b>mowing</b></a>')
        self.assertEqual([('bid.pdf', 'Roadside mowing')], parser.links)

    def test_conditional_304_reuses_cached_content(self):
        url = 'https://agency.gov/mowing.pdf'
        self.store.cache(url, 'v1', None, b'%PDF-cached', 'application/pdf')
        fetcher = Fetcher(self.store, ['agency.gov'], delay=0)
        with patch.object(fetcher, 'permitted', return_value=True), patch.object(fetcher, 'raw') as raw:
            raw.side_effect = urllib.error.HTTPError(url, 304, 'Not modified', {}, None)
            self.assertEqual((b'%PDF-cached', 'application/pdf'), fetcher.get(url))
            self.assertEqual('v1', raw.call_args.args[1]['If-None-Match'])

    def test_failed_pdf_does_not_replace_current_version(self):
        args = ('https://agency.gov/mowing.pdf', 'test', 'PA', 'Mowing', 'https://agency.gov/')
        with patch('highway_contracts.store.PdfReader') as reader:
            reader.return_value.pages = [FakePage()]
            self.store.index(b'%PDF-good', *args)
            reader.side_effect = ValueError('Corrupt PDF')
            with self.assertRaises(ValueError):
                self.store.index(b'%PDF-broken', *args)
        self.assertEqual(1, len(self.store.search('mowing')))


if __name__ == '__main__':
    unittest.main()
