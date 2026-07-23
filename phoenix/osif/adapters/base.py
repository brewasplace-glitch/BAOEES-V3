"""Abstract adapter contract for Phoenix OSIF."""

from abc import ABC, abstractmethod

from ..contracts import (
    ApplicationDescriptor,
    ExecutionRequest,
    ExecutionResult,
    HealthStatus,
)


class OSIFAdapter(ABC):
    @abstractmethod
    def descriptor(self) -> ApplicationDescriptor:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> HealthStatus:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: ExecutionRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError
