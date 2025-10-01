from typing import Dict, Any

def calculate_runtime_cost(tokens: int, latency: float, cost_per_token: float) -> Dict[str, Any]:
    """Calculate the runtime cost based on tokens, latency, and cost per token.

    Args:
        tokens (int): The number of tokens processed.
        latency (float): The latency in seconds.
        cost_per_token (float): The cost per token in the currency of choice.

    Returns:
        Dict[str, Any]: A dictionary containing the total cost and additional metrics.
    """
    total_cost = tokens * cost_per_token
    return {
        "total_cost": total_cost,
        "tokens": tokens,
        "latency": latency,
        "cost_per_token": cost_per_token
    }