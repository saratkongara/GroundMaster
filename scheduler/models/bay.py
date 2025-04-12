from dataclasses import dataclass
from typing import Dict

@dataclass
class Bay:
    number: str  # Unique identifier for the bay (e.g., "A1", "B2")
    travel_time: Dict[str, int]  # Mapping of destination bay numbers to travel durations (in minutes)
