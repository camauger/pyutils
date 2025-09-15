"""Secure password generator CLI with character set controls and logging.

Generates cryptographically secure passwords using `secrets` with options to
include/exclude character classes, avoid ambiguous characters, and require at
least one character from each selected class.
"""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import string
import sys
from typing import List, Sequence

logger = logging.getLogger(__name__)


class PasswordGenerationError(ValueError):
    """Raised when password generation constraints cannot be satisfied."""


AMBIGUOUS_CHARS = set("Il1O0")


def build_alphabets(
    use_lower: bool,
    use_upper: bool,
    use_digits: bool,
    use_symbols: bool,
    avoid_ambiguous: bool,
) -> List[str]:
    alphabets: List[str] = []
    if use_lower:
        lower = string.ascii_lowercase
        if avoid_ambiguous:
            lower = "".join(ch for ch in lower if ch not in AMBIGUOUS_CHARS)
        alphabets.append(lower)
    if use_upper:
        upper = string.ascii_uppercase
        if avoid_ambiguous:
            upper = "".join(ch for ch in upper if ch not in AMBIGUOUS_CHARS)
        alphabets.append(upper)
    if use_digits:
        digits = string.digits
        if avoid_ambiguous:
            digits = "".join(ch for ch in digits if ch not in AMBIGUOUS_CHARS)
        alphabets.append(digits)
    if use_symbols:
        symbols = string.punctuation
        alphabets.append(symbols)
    return [a for a in alphabets if a]


def generate_password(
    length: int,
    use_lower: bool = True,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    avoid_ambiguous: bool = False,
    require_each_class: bool = True,
) -> str:
    if length <= 0:
        raise PasswordGenerationError("length must be > 0")

    alphabets = build_alphabets(
        use_lower=use_lower,
        use_upper=use_upper,
        use_digits=use_digits,
        use_symbols=use_symbols,
        avoid_ambiguous=avoid_ambiguous,
    )
    if not alphabets:
        raise PasswordGenerationError("No character classes selected")

    sysrand = secrets.SystemRandom()
    if require_each_class and length < len(alphabets):
        raise PasswordGenerationError(
            f"length must be >= number of selected classes ({len(alphabets)}) when require_each_class is True"
        )

    # Start with at least one from each class if required
    chars: List[str] = []
    if require_each_class:
        for a in alphabets:
            chars.append(sysrand.choice(a))

    pool = "".join(alphabets)
    while len(chars) < length:
        chars.append(sysrand.choice(pool))

    # Shuffle to avoid predictable class positions
    sysrand.shuffle(chars)
    return "".join(chars)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate secure passwords with configurable character sets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--length", type=int, default=16, help="Password length")
    parser.add_argument(
        "--count", type=int, default=1, help="Number of passwords to generate"
    )

    # Character class toggles
    parser.add_argument(
        "--no-lower",
        dest="use_lower",
        action="store_false",
        help="Exclude lowercase letters",
    )
    parser.add_argument(
        "--no-upper",
        dest="use_upper",
        action="store_false",
        help="Exclude uppercase letters",
    )
    parser.add_argument(
        "--no-digits", dest="use_digits", action="store_false", help="Exclude digits"
    )
    parser.add_argument(
        "--no-symbols", dest="use_symbols", action="store_false", help="Exclude symbols"
    )
    parser.set_defaults(
        use_lower=True, use_upper=True, use_digits=True, use_symbols=True
    )

    parser.add_argument(
        "--avoid-ambiguous", action="store_true", help="Avoid characters like I,l,1,O,0"
    )
    parser.add_argument(
        "--no-require-each",
        dest="require_each",
        action="store_false",
        help="Do not enforce at least one character from each selected class",
    )
    parser.set_defaults(require_each=True)

    parser.add_argument("--json", action="store_true", help="Output as JSON array")
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
        passwords = [
            generate_password(
                length=args.length,
                use_lower=args.use_lower,
                use_upper=args.use_upper,
                use_digits=args.use_digits,
                use_symbols=args.use_symbols,
                avoid_ambiguous=args.avoid_ambiguous,
                require_each_class=args.require_each,
            )
            for _ in range(max(1, args.count))
        ]
    except PasswordGenerationError as ex:
        logger.error(str(ex))
        return 2

    if args.json:
        print(json.dumps(passwords))
    else:
        for pw in passwords:
            print(pw)

    return 0


if __name__ == "__main__":
    sys.exit(main())
