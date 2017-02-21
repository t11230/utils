import struct
import binascii

class BinaryPatcher(object):
    def __init__(self, input_fname):
        super(BinaryPatcher, self).__init__()
        with open(input_fname, 'rb') as fobj:
            self.data = fobj.read()
        self.cursor = 0

    def seek(self, offs):
        self.cursor = offs

    def read(self, fmt, **kwargs):
        offs = self.cursor
        if 'offs' in kwargs:
            offs = kwargs['offs']

        v = struct.unpack_from(fmt, self.data, offs)
        self.cursor = offs + struct.calcsize(fmt)
        return v
        
    def write(self, fmt, *values, **kwargs):
        offs = self.cursor
        if 'offs' in kwargs:
            offs = kwargs['offs']
        size = struct.calcsize(fmt)

        s = struct.pack(fmt, *values)
        self.data = self.data[:offs] + s + self.data[offs+size:]
        self.cursor = offs+size

    def insert(self, offs, size, data=None):
        if data is None:
            data = '\x00'*size

        self.data = self.data[:offs] + data + self.data[offs:]

    def cut(self, offs, size):
        orig = self.data[offs:offs+size]
        self.data = self.data[:offs] + self.data[offs+size:]
        return orig

    def write_file(self, output_fname):
        with open(output_fname, 'wb') as fobj:
            fobj.write(self.data)

def main():
    import os
    with open('inputfile', 'wb') as fobj:
        fobj.write('\xAA\x11\x22\x33\x44\x55\x66\x77')

    b = BinaryPatcher('inputfile')
    
    v = b.read('<I', offs=0x0)[0]
    print('Read 0x{:08X}'.format(v))
    assert v == 0x332211AA
    
    b.write('<I', 0xFFFFFFFF, offs=0x4)
    v = b.read('<I', offs=0x2)[0]
    print('Read 0x{:08X}'.format(v))
    assert v == 0xFFFF3322

    b.insert(0x0, 0x4)
    v = b.read('<I', offs=0x0)[0]
    print('Read 0x{:08X}'.format(v))
    assert v == 0x00000000

    v = b.cut(0x6, 4)
    print('Cut {}'.format(binascii.hexlify(v)))
    assert v == '\x22\x33\xFF\xFF'

    b.write_file('outputfile')

    with open('outputfile', 'rb') as fobj:
        v = fobj.read()
        assert v == '\x00\x00\x00\x00\xAA\x11\xFF\xFF'

    os.remove('inputfile')
    os.remove('outputfile')

if __name__ == '__main__':
    main()