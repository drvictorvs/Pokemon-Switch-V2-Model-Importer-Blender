class FileError(Exception):
    def __init__(self, ext, message):
        if message is None:
            message = f"There should be at least one {ext} file referenced in the TRMDL file."
        super().__init__(message)
