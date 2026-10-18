from enum import Enum


class ExtractionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"


class FactStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"


class ProcedureStatus(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"


class ConfirmationMethod(str, Enum):
    UNCONFIRMED = "UNCONFIRMED"
    CORROBORATED_3X = "CORROBORATED_3X"
    USER_CONFIRMED = "USER_CONFIRMED"


class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    OFFLINE = "OFFLINE"


class HandoffStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MemoryTier(str, Enum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    COORDINATION = "COORDINATION"