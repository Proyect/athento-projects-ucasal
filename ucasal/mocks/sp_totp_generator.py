class TOTPGenerator:
    def __init__(self, key, token_validity_seconds=300):
        self.key = key
        self.token_validity_seconds = token_validity_seconds
        self.verified = True
    def verify_token(self, otp, drift):
        self.verified = True
