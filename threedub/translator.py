import logging
from collections import MutableMapping
from .models import ModelTranslator
from .bases import Slicer

log = logging.getLogger(__name__)

class Metadata(MutableMapping):
    def __init__(self, keys=None):
        if keys is None:
            keys = {}
        self.data = keys.copy()
        self.data.setdefault("total_filament", "1")

    def __getitem__(self, name):
        return self.data[name]
        
    def __setitem__(self, name, value):
        self.data[name] = value
        
    def __delitem__(self, name):
        del self.data[name]
           
    def __len__(self):
        return len(self.data)
        
    def __iter__(self):
        return iter(self.data)
        
        
class GCodeTranslator(object):
    def __init__(self, model, slicer):
        self.model = model
        self.slicer = slicer

    def translate(self, gcode, filename):
        # Translate from slicer    
        log.debug("Translating gcode to model {} using slicer {}".format(self.model, self.slicer))
        slicers = {s.name: s for s in Slicer.implementations()}
        values = Metadata()
        if self.slicer == "auto":
            for slicer in slicers.values():
                inst = slicer()
                try:
                    if inst.detect(gcode):
                        values = Metadata(inst.metadata(gcode))
                        log.debug("Appears to be {} output".format(inst.name))
                        break
                except Exception as e:
                    log.exception("Slicer translation '{}' failed".format(inst))
        else:
            if self.slicer.name in slicers:
                slicer = slicers[self.slicer.name]()
                values = Metadata(slicer.metadata(gcode))
            else:
                raise Exception("Slicer {} not found".format(self.slicer))

        # Set filename
        values['filename'] = filename
        log.debug("Values for translation: {}".format(values))

        # Translate to model
        model = [t for t in ModelTranslator.implementations() if t.model == self.model]
        if model:
            model[0]().translate(gcode, values)
        else:
            log.error("Model translator not found: {}".format(self.model))
