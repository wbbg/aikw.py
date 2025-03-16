class DataWriter:
    def __init__(self, data=[], options={}):
        self.options = options
        self.data = data

    def setData(self, data):
        self.data['data'] = data

    def __str__(self):
        return str(self.options['data'])

    def write(self):
        pass


class SimpleWriter(DataWriter):
    def __init__(self, data=[], options={}):
        super().__init__(data, options)

    def write(self):
        from pprint import pprint as pp
        pp(self.data)


class JsonWriter(DataWriter):
    INDENT = 2

    def __init__(self, data=[], options={}):
        super().__init__(data, options)

    def write(self):
        import json
        if ('filename' in self.options) and self.options['filename']:
            with open(self.options['filename'], "w") as f:
                json.dump(self.data, f, indent=self.INDENT)
        else:
            print(json.dumps(self.data, indent=self.INDENT))
