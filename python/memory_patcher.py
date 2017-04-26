#!/usr/bin/env python
"""Handles loading multiple binary files, inspecting them and patching them.
"""
import struct

from typing import IO, Optional, Tuple


class InvalidAddressException(Exception):
    """Raised when an address cannot be mapped to a section"""
    pass


class WriteException(Exception):
    """Raised when writing to a non-writeable segment"""
    pass


class MemoryPatcher(object):
    def __init__(self):
        super(MemoryPatcher, self).__init__()
        self.segments = []

    def get_segment(self, addr):
        # type: (int) -> Optional[Segment]
        """Gets the segment that contains addr or None if one is not 
        found."""
        for segment in self.segments:
            if addr in segment:
                return segment
        return None

    def get_segment_by_name(self, name):
        # type: (str) -> Optional[Segment]
        """Gets a segment by name or None is one is not found."""
        for segment in self.segments:
            if segment.name == name:
                return segment
        return None

    def addr_to_segment_offset(self, addr):
        # type: (int) -> Tuple[Segment, int]
        """Get the offset into a segment for a given address"""
        segment = self.get_segment(addr)
        if segment is None:
            raise InvalidAddressException(
                'No matching segment for addr 0x{:X}'.format(addr))
        return (segment, segment.addr_to_segment_offset(addr))

    def add_segment(self, base_addr, size, writeable=True, name=None):
        # type: (int, int, bool, str) -> Segment
        """Adds a segment"""
        segment = Segment(base_addr, size, writeable, name)
        self.segments.append(segment)
        return segment

    def read(self, addr, length):
        # type: (int, int) -> bytes
        """Reads bytes from a segment's data at an address"""
        seg = self[addr]
        return seg.read(seg.addr_to_segment_offset(addr), length)

    def write(self, addr, data):
        # type: (int, bytes) -> bytes
        """Replaces data in a segment's data at an address. Returns the 
        bytes that were replaced"""
        seg = self[addr]
        return seg.write(seg.addr_to_segment_offset(addr), data)

    def insert(self, addr, data):
        # type: (int, bytes) -> int
        """Inserts bytes into a segment's data at an address. Returns 
        offset + len(data)"""
        seg = self[addr]
        return seg.insert(seg.addr_to_segment_offset(addr), data)

    def cut(self, addr, length):
        """Removes bytes from a segment's data at an address. Returns the 
        removed bytes"""
        # type: (int, int) -> bytes
        seg = self[addr]
        return seg.cut(seg.addr_to_segment_offset(addr), length)

    def read_struct(self, addr, s):
        # type: (int, struct.Struct) -> Tuple
        """Unpacks a struct from a segment's data at an address. Returns a 
        tuple of values"""
        seg = self[addr]
        return seg.read_struct(seg.addr_to_segment_offset(addr), s)

    def write_struct(self, addr, s, *values):
        # type: (int, struct.Struct, *object) -> bytes
        """Packs a struct into a segment's data at an address. Returns 
        the bytes that were replaced"""
        seg = self[addr]
        return seg.write_struct(seg.addr_to_segment_offset(addr), s, *values)

    def insert_struct(self, addr, s, *values):
        # type: (int, struct.Struct, *object) -> int
        """Packs a struct into a segment's data at an offset. Returns 
        offset + len(data)"""
        seg = self[addr]
        return seg.insert_struct(seg.addr_to_segment_offset(addr), s, *values)

    def __getitem__(self, address):
        # type: (int) -> Segment
        """Gets the segment the contains an address"""
        seg = self.get_segment(address)
        if seg is None:
            raise InvalidAddressException(
                'No matching segment for addr 0x{:X}'.format(address))
        return seg


class Segment(object):
    def __init__(self, base, size, writeable=True, name=None):
        # type: (int, int, bool, str) -> None
        super(Segment, self).__init__()
        if base < 0 or size < 0:
            raise ValueError()
        self.base = base
        self.size = size
        self.end = base + size
        self.writeable = writeable
        self.name = name
        self.data = b''

    def addr_to_segment_offset(self, addr):
        # type: (int) -> int
        """Gets the segment offset for an address"""
        if self.base > addr or addr > self.base + self.size:
            raise InvalidAddressException()
        return addr - self.base

    def load_stream(self, stream):
        # type: (IO[bytes]) -> None
        """Load a stream's data into this segment"""
        data = stream.read()
        if len(data) > self.size:
            raise IndexError()
        self.data = data

    def save_stream(self, stream):
        # type: (IO[bytes]) -> None
        """Save a this segment's data into a stream"""
        stream.write(self.data)

    def read(self, offset, length):
        # type: (int, int) -> bytes
        """Reads bytes from this segment's data at an offset"""
        self._check_offset_len(offset, length)
        return self.data[offset:offset + length]

    def write(self, offset, data):
        # type: (int, bytes) -> bytes
        """Replaces this segment's data at an offset. Returns the bytes that 
        were replaced"""
        self._check_offset_len(offset, len(data))
        orig_data = self.data[offset:offset + len(data)]
        self._update_data(
            self.data[:offset] + data + self.data[offset + len(data):])
        return orig_data

    def insert(self, offset, data):
        # type: (int, bytes) -> int
        """Inserts bytes into this segment's data at an offset. Returns 
        offset + len(data)"""
        if not (0 <= offset <= len(self.data)):
            raise IndexError()
        self._update_data(self.data[:offset] + data + self.data[offset:])
        return offset + len(data)

    def cut(self, offset, length):
        # type: (int, int) -> bytes
        """Removes bytes from this segment's data at an offset. Returns the 
        removed bytes"""
        self._check_offset_len(offset, length)
        orig_data = self.data[offset:offset + length]
        self._update_data(self.data[:offset] + self.data[offset + length:])
        return orig_data

    def read_struct(self, offset, s):
        # type: (int, struct.Struct) -> Tuple
        """Unpacks a struct from this segment's data at an offset. Returns 
        a tuple of values"""
        return s.unpack(self.read(offset, s.size))

    def write_struct(self, offset, s, *values):
        # type: (int, struct.Struct, *object) -> bytes
        """Packs a struct into this segment's data at an offset. Returns 
        the bytes that were replaced"""
        return self.write(offset, s.pack(offset, *values))

    def insert_struct(self, offset, s, *values):
        # type: (int, struct.Struct, *object) -> int
        """Packs a struct into this segment's data at an offset. Returns 
        offset + len(data)"""
        return self.insert(offset, s.pack(*values))

    def __contains__(self, addr):
        """Check if address is in this segment"""
        return self.base <= addr <= self.end

    def _check_offset(self, offset):
        # type: (int) -> None
        if not (0 <= offset < len(self.data)):
            raise IndexError()

    def _check_offset_len(self, offset, length):
        # type: (int, int) -> None
        self._check_offset(offset)
        if not offset + length <= len(self.data):
            raise IndexError()

    def _update_data(self, new_data):
        # type: (bytes) -> None
        if not self.writeable:
            raise WriteException
        self.data = new_data
