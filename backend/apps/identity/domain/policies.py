"""Business policies and invariants for the Identity & Access bounded context.

Encapsulates business rules and invariants as explicit, testable policies
(e.g. JudgeAssignmentPolicy, CompetitionEligibilityPolicy, AgeCategoryPolicy)
so the Open/Closed principle holds — behaviour extends via new policies rather
than edits to core rules (ARCH-001 §4.2, §13.4). Framework-free. Structure only.
"""
