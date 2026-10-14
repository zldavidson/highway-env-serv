import json
import unittest

from highway_contracts.models import (
    Attachment, Diagnostic, DiscoveryBatch, Evidence, Opportunity, detail_url_identity,
)


class ModelTests(unittest.TestCase):
    def opportunity(self, **kwargs):
        return Opportunity(source='agency', source_id='123',
                           source_url='https://agency.gov/123', title='Mowing',
                           observed_at='2026-10-14T10:00:00-04:00', **kwargs)

    def test_nested_json_and_independent_defaults(self):
        first, second = self.opportunity(), self.opportunity()
        first.attachments.append(Attachment(
            url='https://agency.gov/scope.pdf', title='Scope', kind='scope',
            evidence=[Evidence(url=first.source_url, field='attachments',
                               raw_text='Scope', observed_at=first.observed_at,
                               method='source', confidence=1.0)]))
        payload = json.loads(first.to_json())
        self.assertEqual('source', payload['attachments'][0]['evidence'][0]['method'])
        self.assertEqual('unknown', payload['status'])
        self.assertEqual([], second.attachments)

    def test_ambiguous_deadline_is_preserved(self):
        item = self.opportunity(deadline_raw='October 20 at 2 PM')
        self.assertIsNone(item.deadline_at)
        self.assertIsNone(item.deadline_timezone)
        with self.assertRaises(ValueError):
            self.opportunity(deadline_at='2026-10-20T14:00:00')
        self.assertEqual('2026-10-20T14:00:00-04:00',
                         self.opportunity(deadline_at='2026-10-20T14:00:00-04:00').deadline_at)

    def test_empty_requires_complete_and_no_blockers(self):
        self.assertFalse(DiscoveryBatch().verified_empty)
        self.assertTrue(DiscoveryBatch(complete=True).verified_empty)
        for code in ('authentication_required', 'blocked', 'parser_error',
                     'transport_error', 'truncated', 'unsupported'):
            diagnostic = Diagnostic(code=code, message='Unavailable',
                                    severity='warning', retryable=False)
            self.assertFalse(DiscoveryBatch(complete=True, diagnostics=[diagnostic]).verified_empty)
            with self.assertRaises(ValueError):
                DiscoveryBatch(complete=True, diagnostics=[diagnostic, Diagnostic(
                    code='verified_empty', message='No records', severity='info', retryable=False)])

    def test_url_fallback_preserves_distinct_notices(self):
        first, diagnostic = detail_url_identity('https://AGENCY.gov/detail?id=1#section')
        second, _ = detail_url_identity('https://agency.gov/detail?id=2')
        self.assertNotEqual(first, second)
        self.assertEqual('https://agency.gov/detail?id=1', first)
        self.assertEqual('source_id_url_fallback', diagnostic.code)

    def test_json_checkpoint_and_count_validation(self):
        with self.assertRaises(TypeError):
            DiscoveryBatch(next_checkpoint={'cursor': object()})
        with self.assertRaises(ValueError):
            DiscoveryBatch(counts={'listing_records_seen': -1})
        self.assertEqual(4, len(DiscoveryBatch().counts))


if __name__ == '__main__':
    unittest.main()
