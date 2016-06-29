import os
from unittest import TestCase
from tempfile import mkdtemp
import shutil
from threedub.main import threedub

FilesDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

class TestMain(TestCase):
    def setUp(self):
        self.tmp = mkdtemp()
        self.root = FilesDir
        os.chdir(self.tmp)

    def tearDown(self):
        print "Removing {}".format(self.tmp)
        shutil.rmtree(self.tmp)

    def test_main_encrypt_decrypt(self):
        for name in ["cura", "slic3r", "nohead"]:
            basename = "tube_" + name
            threedub([os.path.join(self.root, basename + ".gcode")])
            self.assertTrue(os.path.exists(basename + ".3w"))
            threedub(["-f", "gcode", basename + ".3w"])
            print os.listdir(".")
            self.assertTrue(os.path.exists(basename + ".gcode"))
