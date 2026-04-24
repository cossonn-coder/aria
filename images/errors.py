#aria/images/errors.py

class ProviderError(Exception):
    pass


class TimeoutError(ProviderError):
    pass


class FallbackExhaustedError(ProviderError):
    pass