class UserNotFoundError(Exception):
    pass


class DuplicateUserEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass

class InvalidTokenError(Exception):
    pass
