from pydantic import BaseModel
from typing import List, Optional

class UnsupportedClaim(BaseModel):
    query_id: str
    claim: str
    is_supported: bool

class HallucinationMetrics(BaseModel):
    unsupported_claims: List[UnsupportedClaim]
    unsupported_claim_rate: float

def evaluate_hallucination(samples: List[dict]) -> HallucinationMetrics:
    unsupported_claims = []
    total_claims = 0
    unsupported_count = 0

    for sample in samples:
        total_claims += 1
        # Logic to determine if the claim is supported or not
        if not is_claim_supported(sample):
            unsupported_count += 1
            unsupported_claims.append(UnsupportedClaim(
                query_id=sample['query']['id'],
                claim=sample['generation']['text'],
                is_supported=False
            ))

    unsupported_claim_rate = unsupported_count / total_claims if total_claims > 0 else 0.0

    return HallucinationMetrics(
        unsupported_claims=unsupported_claims,
        unsupported_claim_rate=unsupported_claim_rate
    )

def is_claim_supported(sample: dict) -> bool:
    # Placeholder for actual logic to determine claim support
    return False  # Assume all claims are unsupported for this example