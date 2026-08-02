"""Unit tests for the Identity command messages.

Confirms the commands carry the expected transport fields, apply their defaults,
and are immutable (frozen dataclasses).
"""

from __future__ import annotations

import dataclasses

import pytest

from apps.identity.application.commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    ChangePhoneCommand,
    DeleteUserCommand,
    GrantConsentCommand,
    LockUserCommand,
    RegisterUserCommand,
    RestoreUserCommand,
    UnlockUserCommand,
    VerifyEmailCommand,
    VerifyPhoneCommand,
    WithdrawConsentCommand,
)
from tests.application.identity.fakes import NOW


class TestCommandDefaults:
    def test_register_defaults(self) -> None:
        command = RegisterUserCommand(email="a@example.com", password="pw", first_name="A", last_name="B")
        assert command.middle_name is None
        assert command.phone is None
        assert command.locale is None
        assert command.timezone is None

    def test_optional_fields_default_to_none(self) -> None:
        assert GrantConsentCommand(user_id="u", consent_version="1.0").consent_type is None
        assert WithdrawConsentCommand(user_id="u").consent_type is None
        assert LockUserCommand(user_id="u", reason="r").until is None
        assert DeleteUserCommand(user_id="u").reason is None

    def test_carries_supplied_values(self) -> None:
        command = VerifyEmailCommand(user_id="u", sent_at=NOW)
        assert command.user_id == "u"
        assert command.sent_at == NOW


class TestCommandImmutability:
    def test_representative_command_is_frozen(self) -> None:
        command = ChangeEmailCommand(user_id="u", new_email="a@b.com", current_password="p")
        with pytest.raises(dataclasses.FrozenInstanceError):
            command.new_email = "mutated"  # type: ignore[misc]

    def test_all_commands_are_slotted_dataclasses(self) -> None:
        commands: list[object] = [
            RegisterUserCommand(email="a@b.com", password="p", first_name="A", last_name="B"),
            VerifyEmailCommand(user_id="u", sent_at=NOW),
            ChangeEmailCommand(user_id="u", new_email="a@b.com", current_password="p"),
            ChangePhoneCommand(user_id="u", new_phone="+375291234567"),
            VerifyPhoneCommand(user_id="u", issued_at=NOW),
            ChangePasswordCommand(user_id="u", current_password="old", new_password="p"),
            GrantConsentCommand(user_id="u", consent_version="1.0"),
            WithdrawConsentCommand(user_id="u"),
            LockUserCommand(user_id="u", reason="r"),
            UnlockUserCommand(user_id="u", reason="r"),
            DeleteUserCommand(user_id="u"),
            RestoreUserCommand(user_id="u"),
        ]
        for command in commands:
            assert dataclasses.is_dataclass(command)
            assert not hasattr(command, "__dict__")  # slots=True installs no __dict__
