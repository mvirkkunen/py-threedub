import os
from unittest import TestCase
import threedub.models
import threedub.slicers
from threedub.translator import GCodeTranslator
from threedub.gcode import GCodeFile
from threedub.bases import Slicer
from threedub.davinci import ThreeWFile

Here = os.path.dirname(os.path.abspath(__file__))
TestFiles = os.path.join(Here, "files")

class EncryptTests(TestCase):
    SlicerFiles = {
        "slic3r": "tube_slic3r.gcode",
        "cura": "tube_cura.gcode",
        "xyz": "tube_xyz.gcode",
    }
    def test_encrypt_slicers(self):
        for slicer in Slicer.implementations():
            filename = self.SlicerFiles[slicer.name]
            gcode = GCodeFile.from_file(os.path.join(TestFiles, filename))
            GCodeTranslator("davincijr", slicer).translate(gcode, filename=filename)
            twfile = ThreeWFile(gcode)
        enc = twfile.encrypt()
        roundtrip = ThreeWFile.from_string(enc)
        self.assertEqual(twfile.gcode.header_text, roundtrip.gcode.header_text)
        self.assertEqual(len(twfile.gcode.gcode), len(roundtrip.gcode.gcode))
 
    def test_encrypt_auto(self):
        for slicerfile in self.SlicerFiles.values():
            gcode = GCodeFile.from_file(os.path.join(TestFiles, slicerfile))
            GCodeTranslator("davincijr", "auto").translate(gcode, filename=slicerfile)
            twfile = ThreeWFile(gcode)
        enc = twfile.encrypt()
        roundtrip = ThreeWFile.from_string(enc)
        self.assertEqual(twfile.gcode.header_text, roundtrip.gcode.header_text)
        self.assertEqual(len(twfile.gcode.gcode), len(roundtrip.gcode.gcode))
        
