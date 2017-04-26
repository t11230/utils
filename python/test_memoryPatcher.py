import struct
from io import BytesIO
from unittest import TestCase

from memory_patcher import MemoryPatcher, Segment, InvalidAddressException


class TestMemoryPatcher(TestCase):
    def test_get_segment(self):
        m = MemoryPatcher()
        lower = Segment(0x0, 0x8)
        upper = Segment(0x10, 0x8)
        m.segments += [lower, upper]
        self.assertEqual(m.get_segment(0x0), lower)
        self.assertEqual(m.get_segment(0x4), lower)
        self.assertEqual(m.get_segment(0x8), lower)
        self.assertEqual(m.get_segment(0x10), upper)
        self.assertEqual(m.get_segment(0x14), upper)
        self.assertEqual(m.get_segment(0x18), upper)
        self.assertEqual(m.get_segment(-1), None)
        self.assertEqual(m.get_segment(0x9), None)
        self.assertEqual(m.get_segment(0x19), None)

    def test_get_segment_by_name(self):
        m = MemoryPatcher()
        lower = Segment(0x0, 0x8, name='Lower')
        upper = Segment(0x10, 0x8, name='Upper')
        no_name = Segment(0x20, 0x8)
        m.segments += [lower, upper, no_name]
        self.assertEqual(m.get_segment_by_name('Lower'), lower)
        self.assertEqual(m.get_segment_by_name('Upper'), upper)
        self.assertEqual(m.get_segment_by_name('other'), None)

    def test_addr_to_segment_offset(self):
        m = MemoryPatcher()
        lower = Segment(0x0, 0x8)
        upper = Segment(0x10, 0x8)
        m.segments += [lower, upper]
        self.assertEqual(m.addr_to_segment_offset(0x0), (lower, 0x0))
        self.assertEqual(m.addr_to_segment_offset(0x4), (lower, 0x4))
        self.assertEqual(m.addr_to_segment_offset(0x8), (lower, 0x8))
        self.assertEqual(m.addr_to_segment_offset(0x10), (upper, 0x0))
        self.assertEqual(m.addr_to_segment_offset(0x14), (upper, 0x4))
        self.assertEqual(m.addr_to_segment_offset(0x18), (upper, 0x8))
        self.assertRaises(InvalidAddressException,
                          lambda: m.addr_to_segment_offset(-1))
        self.assertRaises(InvalidAddressException,
                          lambda: m.addr_to_segment_offset(0x9))
        self.assertRaises(InvalidAddressException,
                          lambda: m.addr_to_segment_offset(0x19))

    def test_add_segment(self):
        m = MemoryPatcher()
        self.assertEqual(len(m.segments), 0)
        lower = m.add_segment(0x0, 0x8)
        self.assertTrue(lower in m.segments)
        upper = m.add_segment(0x10, 0x8)
        self.assertTrue(upper in m.segments)

    @staticmethod
    def _setup_data_test():
        m = MemoryPatcher()
        lower = Segment(0x0, 0x8)
        lower_data = struct.pack('<8B', *range(8))
        lower.load_stream(BytesIO(lower_data))
        upper = Segment(0x20, 0x8)
        upper_data = lower_data[::-1]
        upper.load_stream(BytesIO(upper_data))
        m.segments += [lower, upper]
        return lower, lower_data, upper, upper_data, m

    def test_read(self):
        (lower_seg, lower_data,
         upper_seg, upper_data, m) = self._setup_data_test()

        self.assertEqual(m.read(0x0, 4), lower_data[0:4])
        self.assertEqual(m.read(0x4, 4), lower_data[4:8])

        self.assertEqual(m.read(0x20, 4), upper_data[0:4])
        self.assertEqual(m.read(0x24, 4), upper_data[4:8])

        self.assertRaises(InvalidAddressException, lambda: m.read(-1, 4))
        self.assertRaises(IndexError, lambda: m.read(0x6, 4))
        self.assertRaises(IndexError, lambda: m.read(0x8, 2))
        self.assertRaises(IndexError, lambda: m.read(0x26, 4))
        self.assertRaises(InvalidAddressException, lambda: m.read(0x30, 4))

    def test_write(self):
        (lower_seg, lower_data,
         upper_seg, upper_data, m) = self._setup_data_test()

        write_data_0 = struct.pack('<4B', *range(4))[::-1]
        write_data_1 = struct.pack('<4B', *range(4, 8))[::-1]

        self.assertEqual(m.write(0x0, write_data_0), lower_data[0:4])
        self.assertEqual(lower_seg.read(0x0, 4), write_data_0)
        self.assertEqual(m.write(0x4, write_data_1), lower_data[4:8])
        self.assertEqual(lower_seg.read(0x4, 4), write_data_1)

        self.assertEqual(m.write(0x20, write_data_1), upper_data[0:4])
        self.assertEqual(upper_seg.read(0x0, 4), write_data_1)
        self.assertEqual(m.write(0x24, write_data_0), upper_data[4:8])
        self.assertEqual(upper_seg.read(0x4, 4), write_data_0)

        self.assertRaises(InvalidAddressException,
                          lambda: m.write(-1, write_data_0))
        self.assertRaises(IndexError, lambda: m.write(0x6, write_data_0))
        self.assertRaises(IndexError, lambda: m.write(0x8, write_data_0))
        self.assertRaises(IndexError, lambda: m.write(0x26, write_data_0))
        self.assertRaises(InvalidAddressException,
                          lambda: m.write(0x30, write_data_0))

    def test_insert(self):
        (lower_seg, lower_data,
         upper_seg, upper_data, m) = self._setup_data_test()

        insert_data_0 = struct.pack('<4B', *range(4))[::-1]
        insert_data_1 = struct.pack('<4B', *range(4, 8))[::-1]

        self.assertEqual(m.insert(0x0, insert_data_0),
                         0x0 + len(insert_data_0))
        self.assertEqual(lower_seg.read(0x0, 4), insert_data_0)
        self.assertEqual(m.insert(0x4, insert_data_1),
                         0x4 + len(insert_data_1))
        self.assertEqual(lower_seg.read(0x4, 4), insert_data_1)

        self.assertEqual(m.insert(0x20, insert_data_1),
                         0x0 + len(insert_data_1))
        self.assertEqual(upper_seg.read(0x0, 4), insert_data_1)
        self.assertEqual(m.insert(0x24, insert_data_0),
                         0x4 + len(insert_data_0))
        self.assertEqual(upper_seg.read(0x4, 4), insert_data_0)

        self.assertRaises(InvalidAddressException,
                          lambda: m.insert(-1, insert_data_0))
        self.assertRaises(InvalidAddressException,
                          lambda: m.insert(0x9, insert_data_0))
        self.assertRaises(InvalidAddressException,
                          lambda: m.insert(0x30, insert_data_0))

    def test_cut(self):
        (lower_seg, lower_data,
         upper_seg, upper_data, m) = self._setup_data_test()

        self.assertEqual(m.cut(0x0, 4), lower_data[0:4])
        self.assertEqual(lower_seg.read(0x0, 4), lower_data[4:8])

        self.assertEqual(m.cut(0x20, 4), upper_data[0:4])
        self.assertEqual(upper_seg.read(0x0, 4), upper_data[4:8])

        self.assertRaises(InvalidAddressException,
                          lambda: m.cut(-1, 4))
        self.assertRaises(InvalidAddressException,
                          lambda: m.cut(0x9, 4))
        self.assertRaises(InvalidAddressException,
                          lambda: m.cut(0x30, 4))
