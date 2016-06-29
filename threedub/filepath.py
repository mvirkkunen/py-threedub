
import logging
import os

log = logging.getLogger(__name__)

class FilePath(object):
    XYZ3wFile = ".3w"
    GCodeFile = ".gcode"
    Types = set([XYZ3wFile, GCodeFile])

    def __init__(self, path):
        self.path = path

    @property
    def file_type(self):
        ext = os.path.splitext(self.path)[1]
        if ext:
            return ext
        return ""

    @file_type.setter
    def file_type(self, totype):
        if totype and not totype.startswith("."):
            totype = "." + totype
        self.path = os.path.splitext(self.path)[0] + totype
        
