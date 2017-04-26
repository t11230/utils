import struct
from io import BytesIO
from unittest import TestCase

from memory_patcher import Segment, InvalidAddressException, WriteException


class TestSegment(TestCase):
    def test_addr_to_segment_offset(self):
        s = Segment(0, 0x100)
        self.assertEqual(s.addr_to_segment_offset(0), 0)
        self.assertEqual(s.addr_to_segment_offset(0x10), 0x10)
        self.assertEqual(s.addr_to_segment_offset(0x100), 0x100)
        self.assertRaises(InvalidAddressException,
                          lambda: s.addr_to_segment_offset(-1))
        self.assertRaises(InvalidAddressException,
                          lambda: s.addr_to_segment_offset(0x101))

        s = Segment(0x100, 0x100)
        self.assertEqual(s.addr_to_segment_offset(0x100), 0)
        self.assertEqual(s.addr_to_segment_offset(0x110), 0x10)
        self.assertEqual(s.addr_to_segment_offset(0x100+0x100), 0x100)
        self.assertRaises(InvalidAddressException,
                          lambda: s.addr_to_segment_offset(-1))
        self.assertRaises(InvalidAddressException,
                          lambda: s.addr_to_segment_offset(0))
        self.assertRaises(InvalidAddressException,
                          lambda: s.addr_to_segment_offset(0x100 + 0x101))

    def test_load_stream(self):
        data = struct.pack('<8B', *range(8))

        s = Segment(0, 0x100)
        s.load_stream(BytesIO(data))
        self.assertEqual(s.data, data)

        s = Segment(0, 0x0)
        self.assertRaises(IndexError, lambda: s.load_stream(BytesIO(data)))
        self.assertEqual(s.data, b'')

        s = Segment(0, 0x7)
        self.assertRaises(IndexError, lambda: s.load_stream(BytesIO(data)))
        self.assertEqual(s.data, b'')

        s = Segment(0x100, 0x8)
        s.load_stream(BytesIO(data))
        self.assertEqual(s.data, data)

    def test_save_stream(self):
        data = struct.pack('<8B', *range(8))

        s = Segment(0, 0x10)
        stream = BytesIO()
        s.save_stream(stream)
        self.assertEqual(s.data, stream.getvalue())

        s = Segment(0, 0x10)
        s.data = data
        stream = BytesIO()
        s.save_stream(stream)
        self.assertEqual(s.data, stream.getvalue())

    def test_read(self):
        data = struct.pack('<8B', *range(8))
        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.read(0, 8), data)
        self.assertEqual(s.read(0, 1), data[0])
        self.assertEqual(s.read(4, 4), data[4:])
        self.assertRaises(IndexError, lambda: s.read(-1, 4))
        self.assertRaises(IndexError, lambda: s.read(6, 4))
        self.assertRaises(IndexError, lambda: s.read(9, 4))

    def test_write(self):
        data = struct.pack('<8B', *range(8))
        write_data = struct.pack('<4B', *range(4)[::-1])
        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.write(0, write_data), data[0:4])
        self.assertEqual(s.data, write_data + data[4:])

        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.write(4, write_data), data[4:8])
        self.assertEqual(s.data, data[:4] + write_data)

        s = Segment(0, 0x10)
        s.data = data
        self.assertRaises(IndexError, lambda: s.write(-1, write_data))
        self.assertRaises(IndexError, lambda: s.write(6, write_data))
        self.assertRaises(IndexError, lambda: s.write(9, write_data))

        s = Segment(0, 0x10, writeable=False)
        s.data = data
        self.assertRaises(WriteException, lambda: s.write(0, write_data))

    def test_insert(self):
        data = struct.pack('<8B', *range(8))
        insert_data = struct.pack('<4B', *range(4)[::-1])
        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.insert(0, insert_data), 0 + len(insert_data))
        self.assertEqual(s.data, insert_data + data)

        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.insert(6, insert_data), 6 + len(insert_data))
        self.assertEqual(s.data, data[0:6] + insert_data + data[6:8])

        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.insert(8, insert_data), 8 + len(insert_data))
        self.assertEqual(s.data, data[0:8] + insert_data)

        s = Segment(0, 0x10)
        s.data = data
        self.assertRaises(IndexError, lambda: s.insert(-1, insert_data))
        self.assertRaises(IndexError, lambda: s.insert(9, insert_data))

        s = Segment(0, 0x10, writeable=False)
        s.data = data
        self.assertRaises(WriteException, lambda: s.insert(0, insert_data))

    def test_cut(self):
        data = struct.pack('<8B', *range(8))
        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.cut(0, 4), data[0:4])
        self.assertEqual(s.data, data[4:8])

        s = Segment(0, 0x10)
        s.data = data
        self.assertEqual(s.cut(6, 2), data[6:8])
        self.assertEqual(s.data, data[0:6])

        s = Segment(0, 0x10)
        s.data = data
        self.assertRaises(IndexError, lambda: s.cut(-1, 4))
        self.assertRaises(IndexError, lambda: s.cut(6, 4))
        self.assertRaises(IndexError, lambda: s.cut(9, 4))

        s = Segment(0, 0x10, writeable=False)
        s.data = data
        self.assertRaises(WriteException, lambda: s.cut(0, 4))
