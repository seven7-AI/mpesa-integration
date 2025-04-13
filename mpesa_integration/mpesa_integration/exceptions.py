class MpesaError(Exception):
    """Base exception for M-Pesa errors."""
    pass

class MpesaAuthError(MpesaError):
    """Raised when authentication fails."""
    pass

class MpesaPaymentError(MpesaError):
    """Raised when payment initiation fails."""
    pass