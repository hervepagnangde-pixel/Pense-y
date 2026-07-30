from __future__ import annotations


def calculate_simple_return(initial_price: float, final_price: float) -> float:
    """Calcule le rendement simple : (P1 - P0) / P0."""

    if initial_price <= 0:
        raise ValueError("Le prix initial doit être strictement positif.")

    if final_price < 0:
        raise ValueError("Le prix final ne peut pas être négatif.")

    return (final_price - initial_price) / initial_price
