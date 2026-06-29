import errno
from typing import Optional


class UserFacingError(Exception):
    """An anticipated error whose message is safe to show to the user verbatim."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


OS_ERRNO_MESSAGES = {
    errno.ENAMETOOLONG: 'File name is too long.',
    errno.ENOSPC: 'The server is out of storage space.',
    errno.EDQUOT: 'Server storage quota exceeded.',
    errno.EACCES: 'Server storage is not writable.',
    errno.EPERM: 'Server storage is not writable.',
    errno.EROFS: 'Server storage is not writable.',
}


def translate_exception(e: Exception) -> Optional[str]:
    """Map a recognized internal exception to a user-safe message.

    Returns None when the exception is not recognized; callers should then
    fall back to a generic message and keep details in server logs only.
    """
    if isinstance(e, OSError) and e.errno in OS_ERRNO_MESSAGES:
        return OS_ERRNO_MESSAGES[e.errno]
    return None
