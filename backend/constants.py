from enum import Enum


class MESSAGES(str, Enum):
    DEFAULT = lambda msg="": f"{msg if msg else ''}"


class ERROR_MESSAGES(str, Enum):
    def __str__(self) -> str:
        return super().__str__()

    DEFAULT = lambda err="": f"Etwas ist schiefgelaufen. Enthält deine Datei Text?/\n{err if err else ''}"
    ENV_VAR_NOT_FOUND = "Required environment variable not found. Terminating now."
    CREATE_USER_ERROR = "Oops! Something went wrong while creating your account. Please try again later. If the issue persists, contact support for assistance."
    DELETE_USER_ERROR = "Oops! Something went wrong. We encountered an issue while trying to delete the user. Please give it another shot."
    EMAIL_TAKEN = "Diese E-Mail ist bereits registriert. Melden Sie sich mit Ihrem bestehenden Konto an oder wählen Sie eine andere E-Mail-Adresse."
    USERNAME_TAKEN = (
        "Dieser Benutzername ist bereits registriert. Bitte wählen Sie einen anderen Benutzernamen."
    )
    COMMAND_TAKEN = "Uh-oh! This command is already registered. Please choose another command string."
    FILE_EXISTS = "Uh-oh! This file is already registered. Please choose another file."

    NAME_TAG_TAKEN = "Uh-oh! This name tag is already registered. Please choose another name tag string."
    INVALID_TOKEN = (
        "Deine Sitzung ist abgelaufen oder dein Token ist ungültig. Bitte melde dich erneut an."
    )
    INVALID_CRED = "Die angegebene E-Mail oder das Passwort ist falsch. Bitte prüfen Sie Ihre Eingaben auf Tippfehler und versuchen Sie, sich erneut anzumelden."
    INVALID_EMAIL_FORMAT = "The email format you entered is invalid. Please double-check and make sure you're using a valid email address (e.g., yourname@example.com)."
    INVALID_PASSWORD = (
        "The password provided is incorrect. Please check for typos and try again."
    )
    UNAUTHORIZED = "401 Unauthorized"
    ACCESS_PROHIBITED = "Derzeit sind Neuanmeldungen deaktiviert. Kontaktiere einen Adminstrator oder versuche es später erneut."
    ACTION_PROHIBITED = (
        "The requested action has been restricted as a security measure."
    )

    FILE_NOT_SENT = "FILE_NOT_SENT"
    FILE_NOT_SUPPORTED = "Oops! It seems like the file format you're trying to upload is not supported. Please upload a file with a supported format (e.g., JPG, PNG, PDF, TXT) and try again."

    NOT_FOUND = "We could not find what you're looking for :/"
    USER_NOT_FOUND = "We could not find what you're looking for :/"
    API_KEY_NOT_FOUND = "Oops! It looks like there's a hiccup. The API key is missing. Please make sure to provide a valid API key to access this feature."
    MALICIOUS = "Unusual activities detected, please try again in a few minutes."

    PANDOC_NOT_INSTALLED = "Pandoc is not installed on the server. Please contact your administrator for assistance."
