"""Storage-layer exceptions with safe user-facing messages."""


class StorageCorruptError(Exception):
    """Raised when encrypted user or session data cannot be read."""

    USER_MESSAGE = (
        "Your saved data could not be read. Please sign in again."
    )

    def __init__(self, detail: str = "") -> None:
        """Store an internal detail string for server-side logging."""
        self.detail = detail
        super().__init__(self.USER_MESSAGE)
