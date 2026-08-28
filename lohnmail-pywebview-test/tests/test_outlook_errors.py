from __future__ import annotations

import unittest

from core.mailer import _assign_windows_outlook_account, _friendly_windows_outlook_error


class FakeAccount:
    def __init__(self, address: str) -> None:
        self.SmtpAddress = address
        self.DisplayName = address


class FakeOleObject:
    def __init__(self, message) -> None:
        self.message = message
        self.calls = []

    def Invoke(self, *args) -> None:
        self.calls.append(args)
        self.message.selected_account = args[-1]


class LowLevelOnlyMessage:
    def __init__(self) -> None:
        self.selected_account = None
        self._oleobj_ = FakeOleObject(self)

    @property
    def SendUsingAccount(self):
        return self.selected_account

    @SendUsingAccount.setter
    def SendUsingAccount(self, account) -> None:
        raise RuntimeError("late-bound setter failed")


class OutlookErrorTests(unittest.TestCase):
    def test_mapi_login_failure_has_actionable_message(self) -> None:
        error = _friendly_windows_outlook_error(
            Exception("Microsoft Outlook: Der Server steht nicht zur Verfügung (-2147221231)")
        )

        message = str(error)
        self.assertIn("MAPI-Profil", message)
        self.assertIn("Outlook Classic", message)
        self.assertNotIn("-2147221231", message)

    def test_unknown_com_error_is_not_exposed_raw(self) -> None:
        error = _friendly_windows_outlook_error(Exception("raw COM tuple"))

        self.assertIn("Outlook-Classic-Konten", str(error))
        self.assertNotIn("raw COM tuple", str(error))

    def test_sender_account_uses_low_level_property_setter(self) -> None:
        account = FakeAccount("lohnbuchhaltung@example.de")
        message = LowLevelOnlyMessage()

        _assign_windows_outlook_account(message, account, account.SmtpAddress)

        self.assertIs(message.SendUsingAccount, account)
        self.assertEqual(message._oleobj_.calls[0][0], 64209)
        self.assertFalse(hasattr(message, "SentOnBehalfOfName"))

    def test_sender_selection_failure_never_falls_back_to_on_behalf(self) -> None:
        account = FakeAccount("lohnbuchhaltung@example.de")
        message = LowLevelOnlyMessage()
        message._oleobj_.Invoke = lambda *args: None

        with self.assertRaisesRegex(RuntimeError, "im Auftrag von"):
            _assign_windows_outlook_account(message, account, account.SmtpAddress)

        self.assertFalse(hasattr(message, "SentOnBehalfOfName"))


if __name__ == "__main__":
    unittest.main()
