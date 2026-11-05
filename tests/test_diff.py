"""Synthetic snapshots only: these values never enter tracker-data."""
import copy
import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / '.agents/skills/tracker/scripts/diff.py'
spec = importlib.util.spec_from_file_location('tracker_diff', SCRIPT)
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)


def row(url='https://example.com/a', **overrides):
    return dict(name='Test item', url=url, sku='test', region='Москва', price_basis='public',
                regular_price=10000, sale_price=None, has_credit=False, source_status='read_live', **overrides)


def snapshot(*rows):
    return dict(schema_version=1, currency='RUB', items=list(rows))


class DiffTests(unittest.TestCase):
    def compare(self, old, new):
        return diff.compare(old, new, Decimal('1'))

    def test_first_run_and_unchanged(self):
        s = snapshot(row())
        self.assertTrue(self.compare(None, s)['first_run'])
        self.assertEqual(self.compare(None, s)['significant_changes'], [])
        self.assertEqual(self.compare(s, copy.deepcopy(s))['raw_diff'], [])

    def test_decimal_threshold_both_directions(self):
        for price, significant in [(9999.99, False), (9900.01, False), (9900, True), (10100, True)]:
            with self.subTest(price=price):
                new = row(); new['regular_price'] = price
                self.assertEqual(bool(self.compare(snapshot(row()), snapshot(new))['significant_changes']), significant)

    def test_only_significant_product_reported(self):
        a, b = row(), row('https://example.com/b')
        new_a, new_b = copy.deepcopy(a), copy.deepcopy(b)
        new_a['regular_price'] = 9999.99
        new_b['regular_price'] = 9000
        result = self.compare(snapshot(a, b), snapshot(new_b, new_a))
        self.assertEqual(len(result['raw_diff']), 2)
        self.assertEqual([x['url'] for x in result['significant_changes']], [b['url']])

    def test_sale_and_credit_transitions(self):
        original = row(); sale = row(); sale['sale_price'] = 9999.99
        credit = row(); credit['has_credit'] = True
        for before, after, reason in [(original, sale, 'sale_started'), (sale, original, 'sale_ended'),
                                       (original, credit, 'credit_changed'), (credit, original, 'credit_changed')]:
            with self.subTest(reason=reason):
                self.assertIn(reason, self.compare(snapshot(before), snapshot(after))['significant_changes'][0]['reasons'])

    def test_unknown_and_fetch_errors_are_not_discounts(self):
        broken = row(); broken.update(regular_price=None, source_status='unavailable')
        credited = row(); credited['has_credit'] = True
        unknown = row(); unknown['regular_price'] = None
        for before, after in [(credited, broken), (broken, credited), (row(), unknown), (unknown, row())]:
            r = self.compare(snapshot(before), snapshot(after))
            self.assertEqual(r['significant_changes'], [])
            self.assertTrue(r['diagnostics'])

    def test_added_removed_and_context(self):
        a, b = row(), row('https://example.com/b')
        r = self.compare(snapshot(a), snapshot(b))
        self.assertEqual({x['reasons'][0] for x in r['significant_changes']}, {'product_added', 'product_removed'})
        changed = row(); changed.update(region='Санкт-Петербург', regular_price=9000)
        self.assertEqual(self.compare(snapshot(a), snapshot(changed))['significant_changes'], [])

    def test_corrupt_history_rejected(self):
        s = snapshot(row())
        for bad in [snapshot(row(), row()), {'schema_version': 2, 'currency': 'RUB', 'items': []}]:
            with self.assertRaises(ValueError):
                self.compare(bad, s)
        foreign = copy.deepcopy(s); foreign['currency'] = 'USD'
        with self.assertRaises(ValueError):
            self.compare(foreign, s)

    def test_cached_changes_labelled(self):
        a = row(); a['source_status'] = 'read_cached'
        b = copy.deepcopy(a); b['regular_price'] = 9000
        self.assertTrue(self.compare(snapshot(a), snapshot(b))['significant_changes'][0]['cached'])


if __name__ == '__main__':
    unittest.main()
