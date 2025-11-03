from abc import ABC, abstractmethod
from typing import Optional, List, Tuple


class BaseReranker(ABC):
    @abstractmethod
    def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
        pass
