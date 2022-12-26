from enum import Enum


class IntentRequestStatus(str, Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
