class Context:
    def __init__(self, context_dict):
        self.context_dict = context_dict

    def __enter__(self):
        # Update the local variables with the context dictionary
        locals().update(self.context_dict)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Clean up (optional)
        pass