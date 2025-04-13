# models/settings.py
from dataclasses import dataclass

@dataclass
class Settings:
    """
    Configuration for scheduler behavior.
    
    Attributes:
        overlap_tolerance_buffer: Maximum allowed overlap time (minutes) between 
                                consecutive assignments considering travel time
        default_travel_time: Fallback travel time (minutes) when no bay-specific 
                           time is specified
        max_retries: Maximum optimization attempts before giving up
    """
    overlap_tolerance_buffer: int = 15
    default_travel_time: int = 5
    max_retries: int = 3

    def __post_init__(self):
        """Validate configuration values."""
        if self.overlap_tolerance_buffer < 0:
            raise ValueError("Overlap tolerance must be non-negative")
        if self.default_travel_time <= 0:
            raise ValueError("Default travel time must be positive")