"""Shared email rendering helpers used across bounded contexts."""

from .templates import render_transactional_email_html

__all__ = ["render_transactional_email_html"]
