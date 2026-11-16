from __future__ import annotations

import unittest
from unittest import mock

from cdxml_toolkit.chemdraw import progid


class _FakeWinreg:
    """Minimal winreg stand-in: a fixed HKCR tree keyed by "progid\\CLSID"."""

    HKEY_CLASSES_ROOT = "HKCR"

    def __init__(self, tree):
        self.tree = tree

    def OpenKey(self, root, path):
        if root != self.HKEY_CLASSES_ROOT or path not in self.tree:
            raise OSError(2, "The system cannot find the file specified", path)
        return path

    def QueryValueEx(self, key, name):
        return (self.tree[key], 1)


class ProgIdOrderTests(unittest.TestCase):
    def test_the_64_bit_progid_is_tried_before_the_legacy_name(self):
        self.assertEqual(progid.PROGIDS[0], "ChemDraw_x64.Application")
        self.assertEqual(progid.PROGIDS[1], "ChemDraw.Application")


class DispatchTests(unittest.TestCase):
    def _client(self, *, failing=(), result="application"):
        calls = []

        def factory(name):
            calls.append(name)
            if name in failing:
                raise RuntimeError("Invalid class string")
            return f"{result}:{name}"

        client = mock.Mock()
        client.DispatchEx.side_effect = factory
        client.Dispatch.side_effect = factory
        client.GetActiveObject.side_effect = factory
        return client, calls

    def test_dispatch_ex_asks_for_the_64_bit_progid_first(self):
        client, calls = self._client()

        with mock.patch.object(progid, "_client", return_value=client):
            self.assertEqual(progid.dispatch_ex(), "application:ChemDraw_x64.Application")

        self.assertEqual(calls, ["ChemDraw_x64.Application"])

    def test_dispatch_ex_falls_back_to_the_legacy_progid(self):
        client, calls = self._client(failing=("ChemDraw_x64.Application",))

        with mock.patch.object(progid, "_client", return_value=client):
            self.assertEqual(progid.dispatch(), "application:ChemDraw.Application")

        self.assertEqual(calls, ["ChemDraw_x64.Application", "ChemDraw.Application"])

    def test_get_active_falls_back_to_the_legacy_progid(self):
        client, calls = self._client(failing=("ChemDraw_x64.Application",))

        with mock.patch.object(progid, "_client", return_value=client):
            self.assertEqual(progid.get_active(), "application:ChemDraw.Application")

        self.assertEqual(calls, ["ChemDraw_x64.Application", "ChemDraw.Application"])

    def test_the_last_error_is_raised_when_neither_progid_answers(self):
        client, calls = self._client(failing=progid.PROGIDS)

        with mock.patch.object(progid, "_client", return_value=client):
            with self.assertRaises(RuntimeError):
                progid.dispatch_ex()

        self.assertEqual(calls, list(progid.PROGIDS))


class RegistrationTests(unittest.TestCase):
    def test_only_registered_progids_are_listed(self):
        winreg = _FakeWinreg({"ChemDraw_x64.Application\\CLSID": "{C172F840-938F-4A55-A732-4A036E3FBF3D}"})

        with mock.patch.object(progid, "_winreg", return_value=winreg):
            self.assertEqual(progid.registered_progids(), ["ChemDraw_x64.Application"])

    def test_a_host_without_winreg_registers_nothing(self):
        with mock.patch.object(progid, "_winreg", return_value=None):
            self.assertEqual(progid.registered_progids(), [])

    def test_local_server_command_reads_the_first_registered_progid(self):
        winreg = _FakeWinreg({"ChemDraw_x64.Application\\CLSID": "{CLSID-64}"})

        with mock.patch.object(progid, "_winreg", return_value=winreg), mock.patch.object(
            progid, "_local_server", return_value="C:\\ChemDraw\\ChemDraw.exe /Automation"
        ) as local_server:
            self.assertEqual(
                progid.local_server_command(), "C:\\ChemDraw\\ChemDraw.exe /Automation"
            )

        local_server.assert_called_once_with("{CLSID-64}")

    def test_local_server_command_is_none_when_no_progid_is_registered(self):
        with mock.patch.object(progid, "_winreg", return_value=_FakeWinreg({})):
            self.assertIsNone(progid.local_server_command())


if __name__ == "__main__":
    unittest.main()
