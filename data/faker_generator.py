"""Faker-based data generator with CLI options.

Generate fake records with selectable fields, locale, seed, and JSON output.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict, List, Sequence

from faker import Faker  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


AVAILABLE_FIELDS: Dict[str, str] = {
    "name": "name",
    "address": "address",
    "email": "email",
    "phone": "phone_number",
    "company": "company",
    "job": "job",
    "city": "city",
    "country": "country",
    "postcode": "postcode",
    "text": "text",
}


class FakerGenerationError(RuntimeError):
    """Raised when fake data generation fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate fake data records using Faker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        choices=sorted(AVAILABLE_FIELDS.keys()),
        default=["name", "address"],
        help="Fields to include in each record",
    )
    parser.add_argument(
        "--num", type=int, default=1, help="Number of records to generate"
    )
    parser.add_argument("--locale", type=str, help="Faker locale, e.g., en_US, fr_FR")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--json", action="store_true", help="Output as JSON array")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def build_faker(locale: str | None, seed: int | None) -> Any:
    try:
        fk = Faker(locale) if locale else Faker()
        if seed is not None:
            Faker.seed(seed)
        return fk
    except Exception as ex:  # noqa: BLE001
        raise FakerGenerationError(f"Failed to initialize Faker: {ex}") from ex


def generate_record(fake: Any, fields: Sequence[str]) -> Dict[str, Any]:
    record: Dict[str, Any] = {}
    for field in fields:
        provider_attr = AVAILABLE_FIELDS[field]
        try:
            provider = getattr(fake, provider_attr)
            value = provider() if callable(provider) else provider
        except Exception as ex:  # noqa: BLE001
            raise FakerGenerationError(
                f"Failed to generate field '{field}': {ex}"
            ) from ex
        record[field] = value
    return record


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        fake = build_faker(args.locale, args.seed)
    except FakerGenerationError as ex:
        logger.error(str(ex))
        return 2

    if args.num <= 0:
        logger.error("--num must be >= 1")
        return 2

    try:
        records = [generate_record(fake, args.fields) for _ in range(args.num)]
    except FakerGenerationError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        print(json.dumps(records, ensure_ascii=False))
    else:
        for rec in records:
            print(json.dumps(rec, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
