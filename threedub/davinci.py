import logging
import struct
import binascii
import Padding
from io import BytesIO
from Crypto.Cipher.AES import AESCipher, MODE_ECB, MODE_CBC

log = logging.getLogger(__name__)

class ThreeWFile(object):
    @classmethod
    def from_file(cls, path):
        with open(path, 'rb') as f:
            return cls.from_string(f.read())

    @classmethod
    def from_string(cls, string):
        inst = cls()
        inst.decrypt(string)
        return inst

    def decrypt(self, string):
        pass

    def encrypt_header(self):
        key = "@xyzprinting.com"
        iv = chr(0)*16
        aes = AESCipher(key, mode=MODE_CBC, IV=iv)
        header = Padding.appendPadding(self.gcode.header_text)
        return aes.encrypt(header)


    def encrypt(self):
        key = "@xyzprinting.com@xyzprinting.com"
        iv = chr(0)*16
        aes = AESCipher(key, mode=MODE_ECB, IV=iv)
        gcode = self.gcode.gcode_text
        startidx = gcode.find("G21")
        if startidx > 0:
            log.warning("Stripping leading {} bytes from gcode!".format(startidx))
            gcode = gcode[startidx:]
        padded = Padding.appendPadding(gcode)
        enc_gcode = aes.encrypt(padded)

        magic = "3DPFNKG13WTW"
        magic2 = struct.pack("8B", 1, 2, 0, 0, 0, 0, 18, 76)
        blanks = chr(0)*4684
        tag = "TagEJ256"
        magic3 = struct.pack("4B", 0, 0, 0, 68)
        crc32 = binascii.crc32(enc_gcode)
        crcstr = struct.pack(">l", crc32)
        encrypted_header = self.encrypt_header()
        bio = BytesIO()
        bio.write(magic)
        bio.write(magic2)
        bio.write(blanks)
        bio.write(tag)
        bio.write(magic3)
        bio.write(crcstr)
        bio.write((chr(0)*(68 - len(crcstr))))
        bio.write(encrypted_header)
        left = 8192 - bio.tell()
        bio.write((chr(0)*left))
        bio.write(enc_gcode)
        return bio.getvalue()

    def __init__(self, gcode):
        self.gcode = gcode

    def write(self, path):
        with open(path, 'wb') as f:
            f.write(self.encrypt())

