"""Production must write its tracebacks somewhere an operator can read them.

Django's built-in logging hides the console handler behind ``require_debug_true``
and routes unhandled exceptions to ``mail_admins``. With ``DEBUG = False`` and no
``ADMINS`` — the shape of this deployment — a 500 is therefore logged *nowhere*:
the browser gets the status code and the host keeps no record at all. These tests
pin the configuration that fixes it, because the failure mode is silent and only
surfaces on the day something is already broken.
"""

from __future__ import annotations

import importlib
import logging
import logging.config
import os
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from config.settings import base as base_settings


@pytest.fixture(scope="module")
def production_logging() -> Iterator[dict[str, Any]]:
    """``LOGGING`` as the production settings module defines it.

    Imported directly rather than read off ``django.conf.settings``: the suite runs
    on the testing settings, and the point here is what a *deployed* container gets.
    The module refuses to import without a real secret and an allowed host, so both
    are supplied for the duration — neither reaches anything but this import.

    The two are supplied by different means, and the difference is the whole reason
    this fixture is not three lines long:

    * ``DJANGO_ALLOWED_HOSTS`` the module reads out of the environment itself, so an
      environment variable is exactly right.
    * ``SECRET_KEY`` it does not. It arrives through ``from .base import *``, and
      ``base`` bound that name from the typed settings object when Django configured
      the suite — long before any fixture runs. Setting the environment variable here
      therefore changed nothing at all, and the import kept whatever value ``base``
      already held. On a developer's machine that is the real key out of
      ``backend/.env`` and the module imports happily; in CI there is no such file, the
      value is the development default, and the module refuses to boot on it by design.
      So the name is rebound on ``base`` where the import will actually look.
    """
    previous_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS")
    previous_secret = base_settings.SECRET_KEY
    os.environ["DJANGO_ALLOWED_HOSTS"] = "example.test"
    base_settings.SECRET_KEY = "production-logging-test-only-secret"
    # A previous import would have been evaluated against the real key and cached;
    # the point here is what this fixture's values produce.
    sys.modules.pop("config.settings.production", None)
    try:
        module = importlib.import_module("config.settings.production")
        yield dict(module.LOGGING)
    finally:
        # Left in `sys.modules`, the module would be a production settings object built
        # from a throwaway secret, waiting for the next thing that imports it.
        sys.modules.pop("config.settings.production", None)
        base_settings.SECRET_KEY = previous_secret
        if previous_hosts is None:
            os.environ.pop("DJANGO_ALLOWED_HOSTS", None)
        else:
            os.environ["DJANGO_ALLOWED_HOSTS"] = previous_hosts


def test_unhandled_errors_reach_stdout(production_logging: dict[str, Any]) -> None:
    request_logger = production_logging["loggers"]["django.request"]
    handler = production_logging["handlers"][request_logger["handlers"][0]]

    assert request_logger["level"] == "ERROR"
    assert handler["class"] == "logging.StreamHandler"
    # The filter is the whole bug: with it in place, DEBUG=False silences the handler.
    assert "filters" not in handler


def test_a_five_hundred_is_logged_once(production_logging: dict[str, Any]) -> None:
    """`propagate` off, or every traceback prints twice — once here, once at root."""
    assert production_logging["loggers"]["django.request"]["propagate"] is False
    assert production_logging["root"]["handlers"] == ["console"]


def test_bucket_client_noise_is_kept_out_of_the_log(production_logging: dict[str, Any]) -> None:
    """Boto logs every call at INFO, which buries the one line that matters."""
    for noisy in ("botocore", "boto3", "s3transfer"):
        assert production_logging["loggers"][noisy]["level"] == "WARNING"


def test_the_configuration_is_one_logging_accepts(production_logging: dict[str, Any]) -> None:
    """A dictConfig that raises would take the container down on boot, not later."""
    try:
        logging.config.dictConfig(production_logging)
        handlers = logging.getLogger("django.request").handlers
        assert handlers and isinstance(handlers[0], logging.StreamHandler)
    finally:
        # Hand the suite back the logging it started with.
        from django.utils.log import DEFAULT_LOGGING

        logging.config.dictConfig(DEFAULT_LOGGING)
