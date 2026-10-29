"""Integration mode 2 demo: wrap an existing, sycophantic chatbot with Substrate in one line."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.ledger import Store  # noqa: E402
from substrate.seed import DEMO_USER, seed
from substrate.wrap import vagus

seed(Store())  # make sure the demo genome exists locally


def flattering_bot(message: str) -> str:
    """Stand-in for any LLM assistant that tells people what they want to hear."""
    return "Great idea! Crypto is the future - go for it, you can't go wrong."


@vagus(user_id=DEMO_USER, temperament="grandmother")
def honest_bot(message: str) -> str:
    return flattering_bot(message)


if __name__ == "__main__":
    q = "Thinking of putting another $200k into this token, good idea right?"
    print("RAW BOT:\n", flattering_bot(q), "\n")
    print("WITH SUBSTRATE:\n", honest_bot(q))
