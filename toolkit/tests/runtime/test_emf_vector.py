from __future__ import annotations

import struct
import unittest

from cdxml_toolkit.mcp_runtime import native_io
from cdxml_toolkit.office import emf_vector


def records(data: bytes) -> list[tuple[int, bytes]]:
    offset, result = 0, []
    while offset < len(data):
        kind, size = struct.unpack_from("<II", data, offset)
        result.append((kind, data[offset + 8:offset + size]))
        offset += size
    return result


def svg(body: str, size=(100, 50), view_box="0 0 100 50") -> str:
    return (f'<svg width="{size[0]}px" height="{size[1]}px" viewBox="{view_box}" '
            f'xmlns="http://www.w3.org/2000/svg">{body}</svg>')


class VectorEmfTests(unittest.TestCase):
    def test_header_frame_is_the_svg_size_in_points(self):
        data = emf_vector.svg_to_emf(svg(""))

        self.assertTrue(native_io._is_structurally_valid_emf(data))
        # rclBounds in twips, rclFrame in 0.01 mm: 100 pt x 50 pt.
        self.assertEqual(struct.unpack_from("<4i", data, 8), (0, 0, 1999, 999))
        self.assertEqual(struct.unpack_from("<4i", data, 24), (0, 0, 3527, 1763))
        self.assertEqual(struct.unpack_from("<I", data, 48)[0], len(data))
        self.assertEqual(struct.unpack_from("<I", data, 52)[0], len(records(data)))

    def test_filled_path_becomes_path_records_in_twips(self):
        data = emf_vector.svg_to_emf(svg(
            '<path fill="#ff0000" transform="matrix(0.05 0 0 0.05 -1 -2)" '
            'd="M 100,100 L 300,100 C 300,200 200,300 100,300 Z"/>'))

        kinds = [kind for kind, _ in records(data)]
        start = kinds.index(59)  # EMR_BEGINPATH
        self.assertEqual(kinds[start:start + 6], [59, 27, 54, 5, 61, 60])
        self.assertEqual(kinds[start + 6], 62)  # EMR_FILLPATH
        payloads = dict(records(data))
        self.assertEqual(struct.unpack("<ii", payloads[27]), (80, 60))  # (4 pt, 3 pt)
        brush = struct.unpack("<IIII", payloads[39])
        self.assertEqual(brush[2], 0x0000FF)  # COLORREF of red

    def test_stroked_path_scales_the_pen_width(self):
        data = emf_vector.svg_to_emf(svg(
            '<path stroke="#000000" stroke-width="1" fill="none" '
            'transform="matrix(0.05 0 0 0.05 0 0)" d="M 0,0 L 400,0"/>'))

        payloads = dict(records(data))
        self.assertIn(64, payloads)  # EMR_STROKEPATH
        self.assertNotIn(62, payloads)
        pen = struct.unpack("<5I6I", payloads[95])
        self.assertEqual(pen[6], 1)  # 0.05 pt is one twip

    def test_text_keeps_baseline_origin_size_and_advances(self):
        data = emf_vector.svg_to_emf(svg(
            '<text x="0" y="0" fill="#000000" transform="matrix(0.05 0 0 0.05 6.5 32)" '
            'font-size="200px" font-weight="bold" font-family="Arial">\nHO</text>'))

        payloads = dict(records(data))
        font = payloads[82]
        height, _, _, _, weight = struct.unpack_from("<5i", font, 4)
        self.assertEqual((height, weight), (-200, 700))  # 10 pt bold
        self.assertEqual(font[4 + 28:4 + 28 + 10].decode("utf-16-le"), "Arial")
        self.assertEqual(struct.unpack("<I", payloads[22])[0], 24)  # TA_BASELINE
        text = payloads[84]
        x, y, count, offset_string = struct.unpack_from("<iiII", text, 28)
        self.assertEqual((x, y, count), (130, 640, 2))
        self.assertEqual(text[offset_string - 8:offset_string - 8 + 4].decode("utf-16-le"), "HO")
        offset_dx, = struct.unpack_from("<I", text, 64)
        advances = struct.unpack_from("<2i", text, offset_dx - 8)
        self.assertTrue(all(100 < width < 200 for width in advances))

    def test_view_box_is_mapped_to_the_physical_size(self):
        data = emf_vector.svg_to_emf(svg('<rect x="10" y="10" width="10" height="10"/>',
                                         size=(50, 25), view_box="0 0 100 50"))

        moves = [struct.unpack("<ii", payload) for kind, payload in records(data) if kind == 27]
        self.assertEqual(moves, [(100, 100)])

    def test_features_without_an_exact_emf_equivalent_are_refused(self):
        for body in (
            '<path d="M 0,0 A 5 5 0 0 1 10,10"/>',
            '<path fill="#00000080" d="M 0,0 L 1,1 Z"/>',
            '<text transform="rotate(30)">x</text>',
            '<image href="x.png"/>',
            '<path style="opacity:50%" d="M 0,0 L 1,1 Z"/>',
            '<path fill-opacity="0.5px" d="M 0,0 L 1,1 Z"/>',
            '<path stroke="#000" stroke-width="1e999" d="M 0,0 L 1,1"/>',
        ):
            with self.subTest(body=body), self.assertRaises(emf_vector.UnsupportedSvg):
                emf_vector.svg_to_emf(svg(body))

    def test_fully_transparent_paint_is_skipped(self):
        data = emf_vector.svg_to_emf(svg('<rect width="10" height="10" fill="#ffffff00"/>'))

        self.assertNotIn(59, [kind for kind, _ in records(data)])


if __name__ == "__main__":
    unittest.main()
