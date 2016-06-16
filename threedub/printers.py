import serial
import struct
import os
import logging
from io import BufferedRWPair
from .bases import PrinterInterface

log = logging.getLogger(__name__)

class ConnectionError(Exception):
    pass

class PrinterError(Exception):
    pass

class DaVinciJr10(PrinterInterface):
    name = "davincijr"
    QueryCmdA = "XYZv3/query=a"
    UploadCmd = "XYZv3/upload={filename},{size}"
    SaveToSD = ",SaveToSD"
    UploadDidFinishCmd = "XYZv3/uploadDidFinish"

    def __init__(self, device="/dev/ttyACM0"):
        self.device = device
        self._serial = None
        self._io = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc, msg, tb):
        self.close()

    def open(self):
        if self._serial:
            self._serial.close()
        if not os.path.exists(self.device):
            raise ConnectionError("Device {} not found".format(self.device))
        elif not stat.IS_CHR(os.stat(self.device).st_mode):
            raise ConnectionError("Not a serial device: {}".format(self.device))
        self._serial = serial.Serial(
            port=self.device,
            baudrate=115200,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )
        if not self._serial.isOpen():
            raise PrinterError("Serial connection to {} failed".format(device))
        self._io = BufferedRWPair(self._serial, self._serial)

    def close(self):
        if self._serial:
            self._serial.close()

    def write(self, buf):
        log.debug(">>> {}".format(buf))
        self._io.write(buf)

    def read_response(self):
        buf = ""
        line = self._io.readline()
        while line:
            buf += line
            line = self._io.readline()
        return buf

    def expect_ok(self):
        buf = self.read_response()
        if buf != "ok\n":
            raise PrinterError("Communication error: 'ok' not received")

    def parse_status(self, string):
        return string

    def status(self):
        self.write(self.QueryCmdA)
        status = self.read_response()
        return self.parse_status(status)

    def print_data(self, filename, data=None, savetosd=False):
        """
        Print the given data or file.
        """
        if not data and os.path.exists(filename):
            with open(filename, 'rb') as f:
                data = f.read()
                size = os.fstat(f.fileno()).st_size
        else:
            size = len(data)
        path = FilePath(filename)
        path.file_type = ".gcode"
        # Start upload
        cmd = self.UploadCmd.format(filename=path.path, size=size)
        if savetosd:
            cmd += self.SaveToSD
        self.write(cmd)
        self.expect_ok()
        # Send file data
        chunks = (len(data)+12+8191) / 8192
        prev = ""
        blocksize = 8192
        for n in range(0, chunks):
            log.debug("Sending file chunk {}/{}".format(n, chunks))
            chunk = struct.pack(">l", n) + struct.pack(">l", blocksize)
            start = 8192*n
            chunk += content[start:start+8192]
            chunk += "\x00\x00\x00\x00"
            self.write(chunk)
            # Expect "ok\n"
            if n != (chunks-1):
                self.expect_ok()
        # Send finish; expect no response
        self.write(self.UploadDidFinishCmd)
        self.expect_ok()

