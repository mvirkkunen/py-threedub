import logging
import os
from io import BytesIO
from collections import namedtuple

log = logging.getLogger(__name__)

class GCodeBlankLine(object):
    def __str__(self):
        return ""


class GCodeTranslationHeaders(object):
    DaVinciJr10 = """\
; filename = {filename}
; print_time = 1
; machine = daVinciJR10
; filamentid = 50,50
; layer_height = 0.10
; fill_density = 0.00
; raft_layers = 0
; support_material = 0
; support_material_extruder = 1
; support_density = 0.0
; shells = 1
; speed = 10
; brim_width = 0
; total_layers = 1
; version = 15062609
; total_filament = 1.00
; nozzle_diameter = 0.40
; extruder_filament = 1.00:0.00
; dimension = 1.00:1.00:1.00
; extruder = 1
"""

class GCodeHeaderLine(object):
    @classmethod
    def from_string(cls, string):
        string = string.strip("; ")
        parts = map(str.strip, string.split("=", 1))
        if len(parts) > 1:
            return cls(parts[0], parts[1])
        else:
            return cls(parts[0])

    def __init__(self, key, value=None):
        self.key = key
        self.value = value

    def __str__(self):
        if self.value is not None:
            return "; {} = {}".format(self.key, self.value)
        else:
            return "; {}".format(self.key)


class GCodeStatement(object):
    @classmethod
    def from_string(cls, string):
        return cls(string)

    def __init__(self, statement):
        self.statement = statement

    def __str__(self):
        return self.statement

class GCodeFile(object):
    DaVinciJr10 = "davincijr10"
    Models = {
        DaVinciJr10: "DaVinciJr10",
    }
    Headers = {
        DaVinciJr10: GCodeTranslationHeaders.DaVinciJr10,
    }

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls.from_string(f.read())

    @classmethod
    def from_string(cls, string):
        items = []
        for line in BytesIO(string):
            line = line.strip()
            if not line:
                items.append(GCodeBlankLine())
                continue
            if line.startswith(";"):
                log.debug("Read header: {}".format(line))
                items.append(GCodeHeaderLine.from_string(line))
            else:
                if line:
                    log.debug("Read gcode: {}".format(line))
                    items.append(GCodeStatement.from_string(line))
        return cls(items)


    def __init__(self, items):
        self._items = items

    @property
    def items(self):
        return self._items

    @property
    def header(self):
        return filter(lambda x: isinstance(x, GCodeHeaderLine), self._items)

    @property
    def gcode(self):
        return filter(lambda x: isinstance(x, GCodeStatement), self._items)

    @property
    def header_text(self):
        return os.linesep.join(map(str, self.header))

    @property
    def gcode_text(self):
        return os.linesep.join(map(str, self.gcode))

    def write(self, path):
        log.debug("Writing output file: {}".format(path))
        with open(path, "w") as f:
            for item in self._items:
                f.write(str(item))
                f.write(os.linesep)

    def format_header(self, header, info):
        return header.format(**info)

    def header_values(self):
        data = {}
        for item in self.header:
            data[item.key] = item.value
        return data

    def translate(self, model, **kwargs):
        info = self.header_values()
        info.update(kwargs)
        header = self.format_header(self.Headers[model], info)
        newitems = filter(lambda i: not isinstance(i, GCodeHeaderLine), self._items)
        newheader = []
        for line in BytesIO(header):
            newheader.append(GCodeHeaderLine.from_string(line))
        self._items = newheader + newitems


