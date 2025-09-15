"""Product inventory management utility with a typed `Product` dataclass.

Scenario: Manage simple product stock with validation, logging, and a CLI.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class InvalidQuantityError(ValueError):
    """Raised when a provided quantity or amount is invalid (e.g., negative or zero)."""


class InsufficientStockError(RuntimeError):
    """Raised when attempting to sell more units than available in stock."""


class InvalidPriceError(ValueError):
    """Raised when a provided price is invalid (e.g., negative)."""


@dataclass
class Product:
    """A simple product with basic stock operations.

    Attributes:
        name: Product name.
        price: Unit price (must be non-negative).
        quantity: Inventory count (must be non-negative).
        category: Product category name.
    """

    name: str
    price: float
    quantity: int = 0
    category: str = "General"

    def __post_init__(self) -> None:
        if self.price < 0:
            raise InvalidPriceError("Price must be non-negative")
        if self.quantity < 0:
            raise InvalidQuantityError("Quantity must be non-negative")

    def __str__(self) -> str:  # readable presentation
        return (
            f"Product(name={self.name!r}, category={self.category!r}, "
            f"price=${self.price:.2f}, quantity={self.quantity})"
        )

    def restock(self, amount: int) -> None:
        """Increase stock by `amount` (must be > 0)."""
        if amount <= 0:
            raise InvalidQuantityError("Restock amount must be > 0")
        self.quantity += amount
        logger.info(
            f"Restocked {amount} units of {self.name}. Total now: {self.quantity}"
        )

    def sell(self, amount: int) -> None:
        """Decrease stock by `amount` if available (amount must be > 0)."""
        if amount <= 0:
            raise InvalidQuantityError("Sell amount must be > 0")
        if self.quantity < amount:
            raise InsufficientStockError(
                f"Not enough stock to sell {amount} units. Only {self.quantity} available."
            )
        self.quantity -= amount
        logger.info(f"Sold {amount} units of {self.name}. Remaining: {self.quantity}")

    def display_info(self) -> str:
        """Return a multi-line string describing the product."""
        return (
            f"Product: {self.name}\n"
            f"Category: {self.category}\n"
            f"Price: ${self.price:.2f}\n"
            f"Stock: {self.quantity} units"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage a simple product inventory entry.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--name", type=str, default="Item", help="Product name")
    parser.add_argument("--price", type=float, default=0.0, help="Unit price")
    parser.add_argument(
        "--quantity", type=int, default=0, help="Initial stock quantity"
    )
    parser.add_argument(
        "--category", type=str, default="General", help="Product category"
    )

    ops = parser.add_mutually_exclusive_group()
    ops.add_argument("--restock", type=int, help="Increase stock by amount")
    ops.add_argument("--sell", type=int, help="Decrease stock by amount")

    parser.add_argument(
        "--show", action="store_true", help="Display product information"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        product = Product(
            name=args.name,
            price=args.price,
            quantity=args.quantity,
            category=args.category,
        )
    except (InvalidPriceError, InvalidQuantityError) as ex:
        logger.error(str(ex))
        return 2

    try:
        if args.restock is not None:
            product.restock(args.restock)
        if args.sell is not None:
            product.sell(args.sell)
    except (InvalidQuantityError, InsufficientStockError) as ex:
        logger.error(str(ex))
        return 1

    if args.show:
        logger.info(product.display_info())
    else:
        logger.debug(str(product))

    return 0


if __name__ == "__main__":
    sys.exit(main())
