"""Submission-facing wrapper for summary metric generation."""

from __future__ import annotations

from build_final_outputs import summarize_metrics


def main() -> None:
    """Print the core project metrics used in the final deliverables."""

    metrics = summarize_metrics()
    print(f"Funds: {metrics['funds']}")
    print(f"Fund houses: {metrics['fund_houses']}")
    print(f"Categories: {metrics['categories']}")
    print(f"NAV rows: {metrics['nav_rows']}")
    print(f"Transactions: {metrics['transactions_rows']}")


if __name__ == "__main__":
    main()
