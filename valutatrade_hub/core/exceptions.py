"""Domain exceptions for ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Base exception for all ValutaTrade Hub errors."""


class InsufficientFundsError(ValutaTradeError):
    """Raised when a wallet does not have enough funds for an operation."""


class CurrencyNotFoundError(ValutaTradeError):
    """Raised when a requested currency is not found in the system."""


class UserNotFoundError(ValutaTradeError):
    """Raised when a user is not found in the database."""


class UserAlreadyExistsError(ValutaTradeError):
    """Raised when trying to register a username that already exists."""


class AuthenticationError(ValutaTradeError):
    """Raised when login credentials are invalid."""


class RatesExpiredError(ValutaTradeError):
    """Raised when exchange rates have exceeded their TTL."""


class ApiRequestError(ValutaTradeError):
    """Raised when an external API request fails."""
