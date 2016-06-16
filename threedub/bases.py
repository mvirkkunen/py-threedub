class ModelTranslator(object):
    model = ""
    description = ""

    @classmethod
    def implementations(cls):
        return [c for c in cls.__subclasses__() if c is not cls]

    def translate(self, gcode, data):
        pass


class Slicer(object):
    name = ""
    description = ""

    @classmethod
    def implementations(cls):
        return [c for c in cls.__subclasses__() if c is not cls]

    def detect(self, gcode):
        return True

    def metadata(self, gcode):
        """
        Return all translated header values that could
        be extracted from the file.
        """
        pass

class PrinterInterface(object):
    @classmethod
    def implementations(cls):
        return [c for c in cls.__subclasses__() if c is not cls]

    @classmethod
    def model_handler(cls, model):
        for subcls in cls.implementations():
            if subcls.name == model:
                return subcls
        return None

    def status(cls):
        """
        Get printer status
        """
        pass

    def print_file(self, path):
        """
        Print the given data file
        """
        with open(path, 'rb') as f:
            self.print_data(path, f.read())

    def print_data(self, filename, data):
        """
        Print the given data
        """
        pass

