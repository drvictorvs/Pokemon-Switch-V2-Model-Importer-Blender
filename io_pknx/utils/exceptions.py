class TRMSHError(Exception):
    def __init__(self, message="There should be at least one TRMSH file referenced in the TRMDL file."):
        super().__init__(message)
