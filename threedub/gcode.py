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
; total_filament = {total_filament}
; nozzle_diameter = 0.40
; extruder_filament = 1.00:0.00
; dimension = 1.00:1.00:1.00
; extruder = 1
"""

    @classmethod
    def translate_davincijr10(cls, info):
        filament = "1"
        if 'filament used' in info:
            log.debug("Found slic3r-style filament statement")
            # Slic3r
            filament = info['filament used']
        elif 'Filament used' in info:
            # Cura (in meters)
            log.debug("Found cura-style filament statement")
            filament = info['Filament used']
        filament = filament.split()[0]
        if filament.endswith("mm"):
            filament = filament.replace("mm", "")
        elif filament.endswith("m"):
            filament = filament.replace("m", "")
            filament = "{:.1f}".format(float(filament) * 1000.0)
        info['total_filament'] = filament
        return info


class GCodeTranslations(object):
    @classmethod
    def translate_davincijr10(cls, gcode, keywords):
        newcode = []
        for code in gcode:
            if not hasattr(code, "statement"):
                newcode.append(code)
                continue
            if code.statement.startswith("G0 "):
                # DaVinci doesn't use G0 so we make them G1
                statement = code.statement.replace("G0 ", "G1 ")
            else:
                statement = code.statement
            newcode.append(GCodeStatement(statement))
        return newcode


class GCodeHeaderLine(object):
    @classmethod
    def from_string(cls, string):
        string = string.strip("; ")
        # Split on = first
        parts = [str.strip(s) for s in string.split("=", 1)]
        if len(parts) == 1:
            # Try splitting on colon
            parts = [str.strip(s) for s in string.split(":", 1)]
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
    HeaderHandlers = {
        DaVinciJr10: GCodeTranslationHeaders.translate_davincijr10,
    }
    GCodes = {
        DaVinciJr10: GCodeTranslations.translate_davincijr10,
    }

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls.from_string(f.read())

    @classmethod
    def from_string(cls, string):
        header = []
        gcode = [] 
        in_gcode = False
        for line in BytesIO(string):
            line = line.strip()
            if in_gcode:
                target = gcode
            else:
                target = header
            if not line:
                target.append(GCodeBlankLine())
                continue
            if line.startswith(";"):
                target.append(GCodeHeaderLine.from_string(line))
            else:
                if line:
                    in_gcode = True
                    target.append(GCodeStatement.from_string(line))
        return cls(header, gcode)


    def __init__(self, header, gcode):
        self._header = header
        self._gcode = gcode

    @property
    def items(self):
        return self._header + self._gcode

    @property
    def header(self):
        return self._header

    @property
    def gcode(self):
        return self._gcode

    @property
    def text(self):
        return os.linesep.join(map(str, self.items))

    @property
    def header_text(self):
        return os.linesep.join(map(str, self.header))

    @property
    def gcode_text(self):
        return os.linesep.join(map(str, self.gcode))

    def write(self, path):
        log.debug("Writing output file: {}".format(path))
        with open(path, "w") as f:
            for item in self.items:
                f.write(str(item))
                f.write(os.linesep)

    def format_header(self, model, info):
        header = self.Headers.get(model)
        if header:
            if model in self.HeaderHandlers:
                info = self.HeaderHandlers[model](info)
            return header.format(**info)
        else:
            return ""

    def translate_gcode(self, model, keywords):
        gcode = self.GCodes.get(model)
        if gcode:
            return gcode(self._gcode, keywords)
        else:
            return self._gcode

    def header_values(self):
        """
        Reads header values from entire file, even if it doesn't appear
        specifically before the first gcode.
        """
        data = {}
        for item in self.items:
            if isinstance(item, GCodeHeaderLine):
                data[item.key] = item.value
        return data

    def translate(self, model, **kwargs):
        # Update header
        info = self.header_values()
        info.update(kwargs)
        header = self.format_header(model, info)
        newheader = []
        for line in BytesIO(header):
            newheader.append(GCodeHeaderLine.from_string(line))
        self._header = newheader
        # Update body
        self._gcode = self.translate_gcode(model, kwargs)


