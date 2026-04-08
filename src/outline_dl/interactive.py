"""Interactive terminal selection for versions and availabilities."""

from __future__ import annotations


def pick_items(
    label: str,
    items: list[str],
    default_indices: list[int] | None = None,
) -> list[int]:
    """Show a numbered list and let the user toggle selections.

    Returns the selected indices (0-based).

    Controls:
      - Type numbers (space-separated) to toggle selections
      - 'a' to select all, 'n' to select none
      - Enter with no input to confirm current selection
      - 'q' to quit/skip
    """
    if not items:
        return []

    if len(items) == 1:
        print(f"  {label}: {items[0]}")
        return [0]

    selected = set(default_indices or [])

    while True:
        print(f"\n  {label}:")
        for i, item in enumerate(items):
            marker = "*" if i in selected else " "
            print(f"    [{marker}] {i + 1}. {item}")

        print(
            "\n  Enter numbers to toggle, 'a'=all, 'n'=none, Enter=confirm, 'q'=skip"
        )
        choice = input("  > ").strip().lower()

        if choice == "":
            if not selected:
                print("  Nothing selected. Toggle items or press 'q' to skip.")
                continue
            return sorted(selected)
        elif choice == "q":
            return []
        elif choice == "a":
            selected = set(range(len(items)))
        elif choice == "n":
            selected = set()
        else:
            for part in choice.split():
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(items):
                        selected ^= {idx}
                    else:
                        print(f"  Invalid number: {part}")
                except ValueError:
                    print(f"  Invalid input: {part}")
