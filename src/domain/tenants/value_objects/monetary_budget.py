"""MonetaryBudget value object representing tenant monetary and token budgets."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MonetaryBudget:
    """Represents an immutable monetary balance and reservation budget for a tenant."""

    balance: Decimal
    currency: str = "USD"
    reserved_amount: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if not isinstance(self.balance, Decimal):
            object.__setattr__(self, "balance", Decimal(str(self.balance)))
        if not isinstance(self.reserved_amount, Decimal):
            object.__setattr__(self, "reserved_amount", Decimal(str(self.reserved_amount)))

        if self.balance < Decimal("0.00"):
            raise ValueError(f"El saldo monetario no puede ser negativo: {self.balance}")
        if self.reserved_amount < Decimal("0.00"):
            raise ValueError(f"El monto reservado no puede ser negativo: {self.reserved_amount}")
        if self.reserved_amount > self.balance:
            raise ValueError(
                f"El monto reservado ({self.reserved_amount}) "
                f"no puede exceder el saldo total ({self.balance})"
            )
        if len(self.currency) != 3:
            raise ValueError(f"Código de moneda ISO 4217 inválido: {self.currency}")

    @property
    def available_balance(self) -> Decimal:
        """Net available balance for new reservations (balance - reserved_amount)."""
        return self.balance - self.reserved_amount

    def can_reserve(self, estimated_cost: Decimal) -> bool:
        """Checks if there is enough available balance to cover the estimated cost."""
        cost = Decimal(str(estimated_cost))
        return self.available_balance >= cost

    def reserve(self, estimated_cost: Decimal) -> "MonetaryBudget":
        """Returns a new MonetaryBudget with increased reserved amount."""
        cost = Decimal(str(estimated_cost))
        if not self.can_reserve(cost):
            raise ValueError(
                f"Saldo insuficiente para reservar {cost} {self.currency}. "
                f"Disponible: {self.available_balance}"
            )
        return MonetaryBudget(
            balance=self.balance,
            currency=self.currency,
            reserved_amount=self.reserved_amount + cost,
        )

    def settle(self, reserved_cost: Decimal, actual_cost: Decimal) -> "MonetaryBudget":
        """Settles actual cost consumed, releasing prior reservation and deducting actual cost."""
        res = Decimal(str(reserved_cost))
        act = Decimal(str(actual_cost))

        if res > self.reserved_amount:
            raise ValueError(
                f"No se puede liquidar una reserva mayor a la activa: "
                f"{res} > {self.reserved_amount}"
            )

        new_reserved = self.reserved_amount - res
        new_balance = self.balance - act

        if new_balance < Decimal("0.00"):
            raise ValueError(
                f"El costo real ({act}) sobrepasa el saldo total disponible ({self.balance})"
            )

        return MonetaryBudget(
            balance=new_balance,
            currency=self.currency,
            reserved_amount=new_reserved,
        )

    def top_up(self, amount: Decimal) -> "MonetaryBudget":
        """Adds funds to the balance."""
        amt = Decimal(str(amount))
        if amt <= Decimal("0.00"):
            raise ValueError("El monto de recarga debe ser positivo.")
        return MonetaryBudget(
            balance=self.balance + amt,
            currency=self.currency,
            reserved_amount=self.reserved_amount,
        )
