"""COM boundary doubles for portable unit tests; never used by native smoke tests."""
import sys
from types import ModuleType
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def portable_com_boundary(request, monkeypatch):
    if sys.platform == 'win32' or request.path.name not in {
        'test_native_renderer.py', 'test_native_io.py', 'test_office_objects.py'
    }:
        return
    # These modules already supply fake applications/documents. Supply only the
    # unavailable apartment/import boundary, without masking real COM smoke tests.
    pythoncom = ModuleType('pythoncom')
    pythoncom.CoInitialize = mock.Mock()
    pythoncom.CoUninitialize = mock.Mock()
    client = ModuleType('win32com.client')
    client.DispatchEx = mock.Mock(side_effect=AssertionError('Mock application acquisition explicitly'))
    client.GetActiveObject = mock.Mock(side_effect=AssertionError('Mock application acquisition explicitly'))
    win32com = ModuleType('win32com')
    win32com.client = client
    for name, module in {'pythoncom': pythoncom, 'win32com': win32com,
                         'win32com.client': client}.items():
        monkeypatch.setitem(sys.modules, name, module)
