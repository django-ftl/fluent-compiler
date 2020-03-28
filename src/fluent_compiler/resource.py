import attr


@attr.s
class FtlResource(object):
    '''
    Represents an (unparsed) FTL file (contents and optional filename)
    '''
    text = attr.ib()
    filename = attr.ib(default=None)

    @classmethod
    def from_string(cls, text):
        return cls(text)

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'rb') as f:
            return cls(text=f.read().decode('utf-8'), filename=filename)
