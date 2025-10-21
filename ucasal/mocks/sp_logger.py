class SpLogger:
    def __init__(self, app, name):
        self.app = app
        self.name = name
    def entry(self, *args, **kwargs):
        pass
    def exit(self, value=None, exc_info=False):
        return value
    def debug(self, msg, additional_info=None):
        print(f"DEBUG [{self.name}]: {msg}")
    def error(self, msg):
        print(f"ERROR [{self.name}]: {msg}")
