"""Test configuration shared by every layer's suite.

The database is rolled back between tests; the cache is not. Django's locmem
backend lives in the process for the whole run, so anything memoized by one test
is still there for the next one — and now that authorization itself is memoized
(the organization's module entitlements, see
:class:`~apps.organization.application.read_models.EnabledModulesReader`), a test
that withdraws a module would silently close that module for every test that runs
after it.

So the cache is emptied around every test. Tests that assert *on* caching set up
whatever they need inside their own test and still start from a clean slate.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Empty the process-wide cache before and after each test."""
    cache.clear()
    yield
    cache.clear()
