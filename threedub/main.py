import logging
import os
from .gcode import GCodeFile
from .davinci import ThreeWFile
from argparse import ArgumentParser

log = logging.getLogger(__name__)

def build_argparse():
    ap = ArgumentParser()
    ap.add_argument("infile", nargs="?", default="", help="Input gcode file")
    ap.add_argument("outfile", nargs="?", default="", help="Output file")
    ap.add_argument("-d", "--debug", action="store_true", help="Debug logging")
    ap.add_argument("-T", "--no-translate", action="store_false", default=True, dest="translate", help="Don't translate output (keep input headers)")
    ap.add_argument("-E", "--no-encrypt", action="store_false", default=True, dest="encrypt", help="Don't encrypt output (produce gcode)")
    ap.add_argument("-m", "--model", default=GCodeFile.DaVinciJr10, help="Model to translate for")
    ap.add_argument("-l", "--list", default=False, action="store_true", help="List known models")
    return ap

def threedub(argv=None):
    ap = build_argparse()
    args = ap.parse_args(argv)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.list:
        for model in GCodeFile.Models.keys():
            print model
        return 0

    if not args.infile:
        ap.print_help()
        return 0

    outputext = "3w"
    if not args.encrypt:
        outputext = "gcode"

    if not args.outfile:
        args.outfile = os.path.splitext(args.infile)[0] + "." + outext

    infile = GCodeFile.from_file(args.infile)
    if args.translate:
        log.debug("Translating...")
        infile.translate(args.model, filename=os.path.basename(args.outfile))

    if args.encrypt:
        log.debug("Encrypting...")
        outfile = ThreeWFile(infile)
        outfile.write(args.outfile)
    else:
        log.debug("Not encrypting...")
        outfile = GCodeFile(infile.items)
        outfile.write(args.outfile)

