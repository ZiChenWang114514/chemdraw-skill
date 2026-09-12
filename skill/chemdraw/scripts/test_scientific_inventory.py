import unittest
from audit_toolkit_interfaces import _reference_for_module


class ScientificInventoryTests(unittest.TestCase):
    def test_scientific_interfaces_route_to_the_runnable_guide(self):
        for module in ('scientific.tlc','scientific.apparatus','scientific.spectra','scientific.plots','scientific.mechanism'):
            with self.subTest(module=module):
                self.assertEqual(_reference_for_module(module),'scientific-workflows.md')


if __name__=='__main__':
    unittest.main()
