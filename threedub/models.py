import logging
from io import StringIO
from .gcode import GCodeComment
from .bases import ModelTranslator
from string import Formatter

log = logging.getLogger(__name__)

class DaVinciJr10(ModelTranslator):
    model = "davincijr"
    description = "XYZPrinting Da Vinci Jr. 1.0"
    defaults = {
        "filename": "test.gcode",
        "total_filament": 1,
    }
    header_template = """\
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

    def translate(self, gcode, meta):
        self.translate_headers(gcode, meta)
        self.translate_gcode(gcode, meta)

    def translate_headers(self, gcode, meta):
        names = [n[1] for n in Formatter().parse(self.header_template) if n[1] is not None]
        for name in names:
            if not name in meta:
                log.warning("GCode header value '{}' not found; default '{}' used".format(self.defaults[name]))
                meta[name] = self.defaults.get(name, None)
            
        header = self.header_template.format(**meta)
        comments = []
        for line in StringIO(header):
            comments.append(GCodeComment(line.strip()))
        gcode.statements = comments + gcode.gcode

    def translate_gcode(self, gcode, meta):
        """
        Fix up gcode to work with Da Vinci Jr.
        Particularly, translate G0 from Cura to G1.
        """
        for code in gcode.statements:
            if not hasattr(code, "statement"):
                continue
            if code.statement.startswith("G0 "):
                # DaVinci can't use G0's (Cura),
                # so we make these G1's
                code.statement = code.statement.replace("G0 ", "G1 ")
