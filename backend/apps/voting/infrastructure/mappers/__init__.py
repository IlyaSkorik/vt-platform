"""Mappers (anti-corruption layer) between Voting aggregates and ORM rows."""

from __future__ import annotations

from .ballot_mapper import BallotMapper

__all__ = ["BallotMapper"]
