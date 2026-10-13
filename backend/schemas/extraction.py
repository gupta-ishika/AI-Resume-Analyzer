from enum import StrEnum

from pydantic import BaseModel


class ExtractionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExtractionFailureCode(StrEnum):
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    SCANNED_OR_IMAGE_ONLY = "SCANNED_OR_IMAGE_ONLY"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    UNRELIABLE_STRUCTURE = "UNRELIABLE_STRUCTURE"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"


class ExtractionOutcome(BaseModel):
    status: ExtractionStatus
    raw_text: str = ""
    failure_code: ExtractionFailureCode | None = None
    failure_message: str | None = None
    confidence_score: float = 1.0
    needs_review_reason: str | None = None
