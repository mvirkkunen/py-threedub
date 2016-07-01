import serial
import stat
import struct
import os
import logging
import time
import sys
from threading import Thread, Event
from Queue import Queue, Empty
from datetime import datetime, timedelta
from .filepath import FilePath
from .bases import PrinterInterface

log = logging.getLogger(__name__)

class ConnectionError(Exception):
    pass

class PrinterError(Exception):
    pass

class SerialConnection(Thread):
    def __init__(self, device, callback=None, drain=False):
        super(SerialConnection, self).__init__()
        self.device = device
        self._drain = drain
        self.ser = None
        self._inq = Queue()
        self.callback = callback
        self.event = Event()
        self.can_send = True

    def __enter__(self):
        self.open()
        if self._drain:
            self.drain()
        return self

    def __exit__(self, exc, msg, tb):
        if exc:
            log.error("Exiting with exception: {} {}".format(exc, msg))
        self.close()

    def run(self):
        log.debug("Starting reader thread")
        try:
            while not self.event.is_set() and self.ser.isOpen():
                #log.debug("checking...")
                avail = self.ser.inWaiting()
                #log.debug("{} bytes available".format(avail))
                if not avail:
                    #log.debug("Sleeping")
                    self.event.wait(1)
                else:
                    line = None
                    while (line is None or line) and self.ser.isOpen():
                        try:
                            line = self.ser.readline()
                            log.debug("serial readline gave us: {!r}".format(line))
                        except Exception as e:
                            log.debug("Serial read failed")
                            line = ""
                        if line:
                            log.debug("got line {!r}".format(line))
                            if callable(self.callback):
                                log.debug("calling callback")
                                self.callback(line)
                            else:
                                log.debug("putting {}".format(line))
                                self._inq.put(line)
            log.debug("Exited. Serial: {}, Event: {}".format(self.ser.isOpen(), self.event.is_set()))
        except Exception as e:
            log.exception("Failed to read from serial device")

    def open(self):
        if self.ser:
            self.ser.close()
        if not os.path.exists(self.device):
            raise ConnectionError("Device {} not found".format(self.device))
        elif not stat.S_ISCHR(os.stat(self.device).st_mode):
            raise ConnectionError("Not a serial device: {}".format(self.device))
        self.ser = serial.Serial(
            port=self.device,
            baudrate=115200,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )
        if not self.ser.isOpen():
            raise PrinterError("Serial connection to {} failed".format(device))
        self.start()

    def close(self):
        log.debug("Close called")
        self.event.set()
        if self.ser and self.ser.isOpen():
            self.ser.close()

    def drain(self):
        log.debug("Drain...")
        while True:
            try:
                data = self._inq.get_nowait()
                if data:
                    log.debug("Drained: {!r}".format(data))
                else:
                    break
            except Empty as e:
                break

    def clear(self):
        log.debug("Clearing buffer")
        data = None
        while data is None or data:
            data = self.drain()
            if data:
                log.debug("Cleared line {!r}".format(data))

    def dumpformat(self, string):
        if len(string) > 32:
            #out = self.hexformat(string[:16]) + "..." + self.hexformat(string[-16:])
            out = "{!r}".format(string[:16] + "..." + string[-16:])
        else:
            out = repr(string)
        return out
 
    def write(self, data):
        log.debug(">>> {}".format(self.dumpformat(data)))
        self.ser.write(data)
        self.ser.flush()

    def writeline(self, data):
        self.write(data+"\n")

    def readline(self, timeout=None):
        block = False
        if timeout is None or timeout > 0:
            block = True
        log.debug("readline with block {} timeout {}".format(block, timeout))
        try:
            line = self._inq.get(block, timeout)
            log.debug("inq get gave us: {}".format(line))
            return line
        except Empty as e:
            log.debug("Timeout in readline, return empty")
            return ""

    def wait_for_ok(self, timeout=10, expect="ok"):
        log.debug("waiting for ok")
        resp = self.readlines(timeout, expect=expect)
        if not resp or resp.strip() != "ok":
            raise Exception("Expected token not found: {}".format(expect))

    def readlines(self, timeout=None, expect=None):
        buf = ""
        line = None
        log.debug("reading lines with timeout {}...".format(timeout))
        while line is None or line:
            line = self.readline(timeout)
            log.debug("read line {!r}...".format(line))
            if line:
                buf += line
                log.debug("buf is now {!r}".format(buf))
                if line.strip() == expect:
                    log.debug("Token found")
                    break
        return buf



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
       
    def hexformat(self, string):
        out = "".join("{:x}".format(ord(x)) for x in string)
        return out

          
    def _console_print(self, line):
        sys.stdout.write(line)

    def connect(self, callback=None):
        return SerialConnection(self.device, callback, drain=True)

    def console(self):
        with self.connect(self._console_print) as h:
            line = None
            print "Starting direct console to {}. '.quit' to exit".format(self.device)
            line = raw_input("")
            while line is None or line.strip() != ".quit":
                if line.startswith("\\"):
                    line = line.strip()[1:]
                    h.write(line)
                elif line.startswith("."):
                    line = line.strip()[1:]
                    h.write(line+"\r\n")
                else:
                    h.writeline(line.strip())
                line = raw_input("")

    def parse_status(self, string):
        return string

    def status(self):
        status = self.query_cmd("a", expect="$")
        return self.parse_status(status)

    def action_cmd(self, action, expect=None):
        return self.generic_cmd(self.ActionCmd, action, expect)

    def generic_cmd(self, template, value, expect=None):
        cmd = template.format(value)
        return self.bare_cmd(cmd, expect=expect)

    def bare_cmd(self, cmd, expect=None):
        with self.connect() as c:
            c.writeline(cmd)
            log.debug("Reading response...")
            return c.readlines(timeout=3, expect=expect)

    def query_cmd(self, code, expect=None):
        return self.generic_cmd(self.QueryCmd, code, expect=expect)

    def config_cmd(self, value):
        return self.generic_cmd(self.ConfigCmd, value)

    def pause(self):
        self.writeline(self.PauseCmd)

    def resume(self):
        self.writeline(self.ResumeCmd)

    def cancel(self):
        self.writeline(self.CancelCmd)

    def _print_reader(self, line):
        if not line.strip().startswith("ok"):
            self._print_continue = True

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
        with self.connect() as conn:
            opts = ""
            if savetosd:
                opts = self.SaveToSD
            cmd = self.UploadCmd.format(filename=path.path, size=size, option=opts)
            conn.writeline(cmd)
            conn.wait_for_ok()
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
                conn.write(chunk)
                # Expect "ok\n"
                conn.wait_for_ok()

            # Send finish; expect no response
            conn.write(self.UploadDidFinishCmd)
