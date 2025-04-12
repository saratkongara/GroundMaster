from abc import ABC, abstractmethod

class Constraint(ABC):
    """
    Base class for all constraints in the scheduling system.
    """
    @abstractmethod
    def apply(self, model, assignments):
        pass