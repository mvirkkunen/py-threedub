from .bases import Slicer

class Slic3r(Slicer):
    name = "slic3r"
    description = "Slic3r"

    def detect(self, gcode):
        """
        Slic3r is detected if comments use filament_used =
        or contain "Slic3r"
        """
        for stmt in gcode.headers:
            if "Slic3r" in stmt.line:
                return True
            elif "filament_used =" in stmt.line:
                return True
        return False

    def header_values(self, gcode):
        """
        Return all header values that could
        be extracted from the file.
        """
        values = {}
        for cmt in gcode.headers:
            string = cmt.line.strip("; ")
            # Slic3r splits on =
            parts = [s.strip() for s in string.split("=", 1)]
            if len(parts) > 1:
                values[parts[0]] = parts[1]
        return values
        
    def metadata(self, gcode):
        info = self.header_values(gcode)
        meta = {}
        filament = info.get("filament used", "1")
        if filament.endswith("mm"):
            filament = filament.replace("mm", "")
        meta["total_filament"] = filament
        return meta


class XYZSlicer(Slicer):
    name = "xyz"
    description = "XYZ"

    def detect(self, gcode):
        """
        Look for 'total_filament'
        """
        for stmt in gcode.headers:
            if "total_filament" in stmt.line:
                return True
        return False

    def header_values(self, gcode):
        """
        Return all header values that could
        be extracted from the file.
        """
        values = {}
        for cmt in gcode.headers:
            string = cmt.line.strip("; ")
            # XYZ splits on =
            parts = [s.strip() for s in string.split("=", 1)]
            if len(parts) > 1:
                values[parts[0]] = parts[1]
        return values

    def metadata(self, gcode):
        info = self.header_values(gcode)
        meta = {}
        filament = info.get('total_filament', "1").split()[0]
        if filament.endswith("mm"):
            filament = filament.replace("mm", "")
        meta['total_filament'] = filament
        return meta
    
class Cura(Slicer):
    name = "cura"
    description = "Ultimaker Cura"

    def detect(self, gcode):
        """
        Slic3r is detected if comments use filament_used =
        or contain "Slic3r"
        """
        for stmt in gcode.headers:
            if "Filament used:" in stmt.line:
                return True
        return False


    def header_values(self, gcode):
        """
        Return all header values that could
        be extracted from the file.
        """
        values = {}
        for cmt in gcode.headers:
            string = cmt.line.strip("; ")
            # Cura splits on :
            parts = [s.strip() for s in string.split(":", 1)]
            if len(parts) > 1:
                values[parts[0]] = parts[1]
        return values

    def metadata(self, gcode):
        info = self.header_values(gcode)
        meta = {}
        filament = info.get('Filament used', "1").split()[0]
        if filament.endswith("m"):
            filament = filament.replace("m", "")
            filament = "{:.1f}".format(float(filament) * 1000.0)
        meta['total_filament'] = filament
        return meta
