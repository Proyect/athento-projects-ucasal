class SpAthentoConfig:
    @staticmethod
    def get_str(key, is_secret=False):
        return f"mocked_value_for_{key}"
    @staticmethod
    def get_int(key):
        return 300
