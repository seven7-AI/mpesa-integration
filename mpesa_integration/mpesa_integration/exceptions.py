class MpesaAuthError(Exception):
    """Raised when authentication fails."""
    pass

class MpesaPaymentError(Exception):
    """Raised when payment initiation fails."""
    pass

class MpesaTransactionError(Exception):
    """Raised when transaction status check fails."""
    pass