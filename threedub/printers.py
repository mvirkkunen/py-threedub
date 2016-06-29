import serial
import stat
import struct
import os
import logging
import time
from datetime import datetime, timedelta
from .filepath import FilePath
from io import BufferedRWPair
from .bases import PrinterInterface

log = logging.getLogger(__name__)

class ConnectionError(Exception):
    pass

class PrinterError(Exception):
    pass

class DaVinciJr10(PrinterInterface):
    name = "davincijr"
    QueryCmd = "XYZv3/query={}"
    ActionCmd = "XYZv3/action={}"
    ConfigCmd = "XYZv3/config={}"
    UploadCmd = "XYZv3/upload={filename},{size}{option}"
    SaveToSD = ",SaveToSD"
    UploadDidFinishCmd = "XYZv3/uploadDidFinish"
    PauseCmd = "M84 P"
    ResumeCmd = "M84 R"
    CancelCmd = "M84"

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
            self.clear()
            self._io.close()
            self._serial.close()
        if not os.path.exists(self.device):
            raise ConnectionError("Device {} not found".format(self.device))
        elif not stat.S_ISCHR(os.stat(self.device).st_mode):
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
        self.clear()

    def close(self):
        if self._serial:
            self._serial.close()

    def hexformat(self, string):
        out = "".join("{:x}".format(ord(x)) for x in string)
        return out

    def dumpformat(self, string):
        if len(string) > 32:
            #out = self.hexformat(string[:16]) + "..." + self.hexformat(string[-16:])
            out = "{!r}".format(string[:16] + "..." + string[-16:])
        else:
            out = repr(string)
        return out

    def clear(self):
        log.debug("Clearing buffer")
        while self.read_response(timeout=0):
            pass
            
    def writeline(self, buf, addnewline=True):
        if addnewline:
            self.raw_write(buf + "\n")
        else:
            self.raw_write(buf)

    def raw_write(self, buf):
        log.debug(">>> {} bytes: {}".format(len(buf), self.dumpformat(buf)))
        self._io.write(buf)
        self._io.flush()

    def read_response(self, timeout=10, numbytes=None):
        buf = ""
        start = datetime.now()
        now = start
        left = numbytes
        line = self._io.readline()
        while (left is None or left > 0) and ((not buf and (now-start).total_seconds() < timeout) or line):
            if line:
                log.debug("Read: {!r}".format(line))
                buf += line[:numbytes]
                if left:
                    left -= min([numbytes, len(line)])
            line = self._io.readline()
            now = datetime.now()
        return buf

    def console(self):
        with self as h:
            print "Starting direct console to {}. '.quit' to exit".format(self.device)
            line = raw_input("> ")
            while line != ".quit":
                h.writeline(line.strip())
                resp = self.read_response(timeout=1)
                print resp
                line = raw_input("> ")

    def expect_ok(self):
        buf = self.read_response(numbytes=3)
        if buf != "ok\n":
            raise PrinterError("Communication error: 'ok' not received")

    def parse_status(self, string):
        return string

    def status(self):
        status = self.query_cmd("a")
        return self.parse_status(status)

    def action_cmd(self, action):
        return self.generic_cmd(self.ActionCmd, action)

    def generic_cmd(self, template, value):
        cmd = template.format(value)
        return self.bare_cmd(cmd)

    def bare_cmd(self, cmd):
        self.writeline(cmd)
        response = self.read_response()
        return response

    def query_cmd(self, code):
        return self.generic_cmd(self.QueryCmd, code)

    def config_cmd(self, value):
        return self.generic_cmd(self.ConfigCmd, value)

    def pause(self):
        self.writeline(self.PauseCmd)

    def resume(self):
        self.writeline(self.ResumeCmd)

    def cancel(self):
        self.writeline(self.CancelCmd)

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
        opts = ""
        if savetosd:
            opts = self.SaveToSD
        cmd = self.UploadCmd.format(filename=path.path, size=size, option=opts)
        self.writeline(cmd)
        self.expect_ok()
        # Send file data
        chunks = (len(data)+8191) / 8192
        prev = ""
        blocksize = 8192
        for n in range(0, chunks):
            log.debug("Sending file chunk {}/{}".format(n, chunks))
            chunk = struct.pack(">l", n) + struct.pack(">l", blocksize)
            start = 8192*n
            chunk += data[start:start+8192]
            chunk += "\x00\x00\x00\x00"
            self.raw_write(chunk)
            # Expect "ok\n"
            self.expect_ok()
        # Send finish; expect no response
        self.raw_write(self.UploadDidFinishCmd)
        #self.read_response()

