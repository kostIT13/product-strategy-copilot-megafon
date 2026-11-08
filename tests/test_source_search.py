"""Search request validation independent of PostgreSQL."""

import unittest
from unittest.mock import Mock

from product_strategy_agent.application.services.source_search_service import SourceSearchService


class SourceSearchTests(unittest.TestCase):
    def test_valid_request_is_normalized_and_delegated(self):
        port = Mock()
        port.search.return_value = []
        self.assertEqual(SourceSearchService(port).search(" demo ", " retention ", 3), [])
        port.search.assert_called_once_with("demo", "retention", 3)

    def test_invalid_queries_never_reach_adapter(self):
        port = Mock()
        for project, query in (("", "term"), ("demo", " "), ("demo", "!!!"), ("demo", "x" * 1001)):
            with self.subTest(query=query), self.assertRaises(ValueError):
                SourceSearchService(port).search(project, query)
        port.search.assert_not_called()

    def test_invalid_limits_are_rejected(self):
        port = Mock()
        for limit in (0, 51, True, 1.5, "2"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                SourceSearchService(port).search("demo", "term", limit)
        port.search.assert_not_called()
