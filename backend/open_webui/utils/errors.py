import errno

from fastapi import HTTPException

from open_webui.constants import ERROR_MESSAGES


OS_ERROR_MESSAGES = {
    errno.ENAMETOOLONG: 'File name is too long.',
    errno.ENOSPC: 'The server is out of storage space.',
    errno.EDQUOT: 'Server storage quota exceeded.',
    errno.EACCES: 'Server storage is not writable.',
    errno.EPERM: 'Server storage is not writable.',
    errno.EROFS: 'Server storage is not writable.',
}


def error_detail(exc: Exception, fallback: str = '') -> str:
    if isinstance(exc, HTTPException) and exc.detail:
        return exc.detail if isinstance(exc.detail, str) else ERROR_MESSAGES.DEFAULT(fallback)

    if isinstance(exc, OSError) and exc.errno in OS_ERROR_MESSAGES:
        return ERROR_MESSAGES.DEFAULT(OS_ERROR_MESSAGES[exc.errno])

    return ERROR_MESSAGES.DEFAULT(fallback)
