"""Bank accounts."""


class InsufficientFunds(Exception):
    """Raised when an account does not have enough money."""


class Account:
    def __init__(self, owner: str, balance: float = 0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("deposit must be positive")
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("withdrawal must be positive")
        if amount > self.balance:
            raise InsufficientFunds(f"{self.owner} has {self.balance}, needs {amount}")
        self.balance -= amount


def transfer(source: Account, target: Account, amount: float) -> None:
    """Move money between accounts. Either both balances change or neither does."""
    source.withdraw(amount)
    target.deposit(amount)
