import logging
import os
import sys
from . import slicers
from . import models
from . import printers
from .gcode import GCodeFile
from .davinci import ThreeWFile
from .bases import Slicer, ModelTranslator, PrinterInterface
from .filepath import FilePath
from .translator import GCodeTranslator
from argparse import ArgumentParser

log = logging.getLogger(__name__)


def build_argparse():
    ap = ArgumentParser(description="""\
Convert and/or translate a gcode file for use with XYZPrinting 3D printers.

The default behavior translates gcode headers, then encodes to .3w if the
output filename ends with .3w, or conversion is specifically requested.
""")
    ap.add_argument("infile", nargs="?", default="", help="Input file")
    ap.add_argument("outfile", nargs="?", default="", help="Output file")
    ap.add_argument("-d", "--debug", action="store_true", help="Debug logging")
    ap.add_argument("-f", "--output-format", default=None, help="Output file type ({})".format(", ".join(sorted(FilePath.Types))))
    ap.add_argument("-m", "--model", default="davincijr", help="Machine to translate headers for. Set to 'none' for no translation.")
    ap.add_argument("-s", "--slicer", default="auto", help="Flavor of Slicer gcode being read. Tries to autodetect if not given.")
    ap.add_argument("-l", "--list", default=False, action="store_true", help="List known models (for -m) and slicers (for -s)")
    ap.add_argument("-e", "--device", default="/dev/ttyACM0", help="Printer device name or address")
    ap.add_argument("-q", "--status", dest="status", default=False, action="store_true", help="Show printer status")
    ap.add_argument("-r", "--raw", dest="raw", default=False, action="store_true", help="Show raw status values")
    ap.add_argument("-p", "--print", dest="start_print", default=False, action="store_true", help="Print the file to the named device (in addition to encoding and translating) (default: /dev/ttyACM0)")
    ap.add_argument("-c", "--console", dest="console", default=False, action="store_true", help="Open a console for direct communication.")
    return ap


# convert - change from one format to another
#  gcode -> 3w
#  3w -> gcode
# translate - change content keeping file type #  - postprocess gcode (G0->G1)
#  - change gcode headers (to 3w format)
#  - change start gcode
#  - change end gcode
#
# PRINTER commands
# - query
# - print
#
# Can combine:
#  threedub --convert infile.gcode -o outfile.3w --translate xyz --gcode-start

def list_support():
    # List model translators
    print "Models:"
    print "  {:12s}: {}".format("none", "Disable header translation")
    for trans in ModelTranslator.implementations():
        print "  {:12s}: {}".format(trans.model, trans.description)
    print
    # List slicers
    print "Slicers:"
    print "  {:12s}: {}".format("auto", "Auto-detect")
    for slicer in Slicer.implementations():
        print "  {:12s}: {}".format(slicer.name, slicer.description)
    print
    print "Output formats:"
    for t in sorted(FilePath.Types):
        print "  {}".format(t.replace(".", ""))
    print

def process_file(args):
    """
    Take requested actions on the input file.
    Returns a 3-tuple of (3w file, intermediate file, outfile).
    Input file may be none if input was gcode.
    """
    # Figure out output path and/or format.
    inpath = FilePath(args.infile)
    if args.outfile:
        # Infer output_format if not set from file path
        outpath = FilePath(args.outfile)
        if not args.output_format:
            args.output_format = outpath.file_type
    else:
        # Infer output path from infile and output_format
        # If output_format is unset, assume .3w
        outpath = FilePath(os.path.basename(args.infile))
        if not args.output_format:
            args.output_format = FilePath.XYZ3wFile
        outpath.file_type = args.output_format
        args.outfile = outpath.path

    if args.output_format.replace(".", "") not in [t.replace(".", "") for t in FilePath.Types]:
        print >> sys.stderr, "Unknown output format: {}".format(args.output_format)
        return 1

    # Figure out what steps to take to get to output format
    decode = (inpath.file_type == FilePath.XYZ3wFile)
    gcodeformat = args.slicer
    model = args.model
    encode = (args.output_format == FilePath.XYZ3wFile)

    # Decode/open
    twfile = None
    intermediate = None
    outfile = None
    if decode:
        log.debug("Decoding '{}' as 3w".format(args.infile))
        twfile = ThreeWFile.from_file(args.infile)
        intermediate = twfile.gcode
    else:
        log.debug("Reading '{}' as gcode".format(args.infile))
        intermediate = GCodeFile.from_file(args.infile)

    # Translate
    if args.model != "none":
        log.debug("Translating to model '{}' with slicer setting '{}'".format(args.model, args.slicer))
        GCodeTranslator(args.model, args.slicer).translate(intermediate, filename=args.outfile)

    # Encode/write
    if encode:
        log.debug("Encoding to 3w: '{}'".format(args.outfile))
        outfile = ThreeWFile(intermediate)
    else:
        log.debug("Encoding to gcode: '{}'".format(args.outfile))
        outfile = intermediate
    return twfile, intermediate, outfile


def threedub(argv=None):
    ap = build_argparse()
    args = ap.parse_args(argv)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.list:
        list_support()
        return 0

    # Validate args
    printhandler = None
    if args.start_print and args.model == "none":
        log.error("Can't print with model set to 'none'")
        return 1

    # Check for print handler
    if args.start_print or args.status or args.console:
        log.debug("Using '{}' as print device".format(args.device))
        printcls = PrinterInterface.model_handler(args.model)
        log.debug("Found handler for model '{}'".format(args.model))
        if not printcls:
            log.error("Communication with model '{}' not supported".format(args.model))
            return 1
        printhandler = printcls(args.device)

    if printhandler and args.console:
        printhandler.console()
        return 0


    # No input file or status query; show help
    if not args.infile and not args.status and not args.console:
        ap.print_help()
        return 0

    # Status?
    if args.status:
        print printhandler.status(args.raw)

    # Process file and write it if we're not just printing
    # If output file is same as input, don't update it unless user specified the name
    if args.infile:
        pathgiven = args.outfile
        twfile, intermediate, outfile = process_file(args)
        if args.infile != args.outfile or pathgiven:
            outfile.write(args.outfile)
        else:
            log.info("Not overwriting input file: {}. If this is really what you want, specify the output file path".format(args.infile))

    # Print?
    if args.start_print:
        log.debug("Printing file to device '{}'".format(args.device))
        # If we didn't convert before, we need to now
        print_data = None
        if args.output_format == FilePath.XYZ3wFile:
            print_file = outfile
        else:
            print_file = ThreeWFile(intermediate)
            print_data = print_file.encrypt()
        printhandler.print_data(args.outfile, print_data)
