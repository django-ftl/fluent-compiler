class FluentError(ValueError):
    # This equality method exists to make exact tests for exceptions much
    # simpler to write, at least for our own errors.
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other.args == self.args


class FluentFormatError(FluentError):
    pass


class FluentReferenceError(FluentFormatError):
    pass


class FluentCyclicReferenceError(FluentFormatError):
    pass


class FluentDuplicateMessageId(FluentError):
    pass


class FluentJunkFound(FluentError):
    def __init__(self, *args):
        super().__init__(*args)
        self.message = args[0]
        self.annotations = args[1]
