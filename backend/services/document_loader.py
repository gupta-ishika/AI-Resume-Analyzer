import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from backend.schemas.extraction import (
    ExtractionFailureCode,
    ExtractionOutcome,
    ExtractionStatus,
)


class DocumentLoaderService:
    """Service to safely extract raw text from PDF and DOCX documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    @classmethod
    def extract_text_from_bytes(cls, content: bytes, filename: str) -> ExtractionOutcome:
        """Extract text from file bytes with error handling and failure categorization."""
        ext = Path(filename).suffix.lower()

        if ext not in cls.SUPPORTED_EXTENSIONS:
            return ExtractionOutcome(
                status=ExtractionStatus.FAILED,
                failure_code=ExtractionFailureCode.UNSUPPORTED_FORMAT,
                failure_message=(
                    f"Unsupported file extension '{ext}'. Only PDF and DOCX are supported."
                ),
            )

        if not content or len(content.strip()) == 0:
            return ExtractionOutcome(
                status=ExtractionStatus.FAILED,
                failure_code=ExtractionFailureCode.EMPTY_DOCUMENT,
                failure_message="The uploaded document is completely empty.",
            )

        try:
            if ext == ".pdf":
                return cls._extract_pdf(content)
            elif ext == ".docx":
                return cls._extract_docx(content)
        except Exception as e:
            return ExtractionOutcome(
                status=ExtractionStatus.FAILED,
                failure_code=ExtractionFailureCode.CORRUPTED_FILE,
                failure_message=f"Unable to read file content: {str(e)}",
            )

        return ExtractionOutcome(
            status=ExtractionStatus.FAILED,
            failure_code=ExtractionFailureCode.EXTRACTION_ERROR,
            failure_message="Unknown extraction error occurred.",
        )

    @classmethod
    def _extract_pdf(cls, content: bytes) -> ExtractionOutcome:
        try:
            reader = PdfReader(io.BytesIO(content))
            extracted_pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    extracted_pages.append(text.strip())

            full_text = "\n\n".join(extracted_pages).strip()

            if not full_text:
                return ExtractionOutcome(
                    status=ExtractionStatus.FAILED,
                    failure_code=ExtractionFailureCode.SCANNED_OR_IMAGE_ONLY,
                    failure_message=(
                        "Document contains no extractable text. Scanned / image-only documents "
                        "are not supported; please upload a text-based PDF or DOCX."
                    ),
                )

            return ExtractionOutcome(
                status=ExtractionStatus.SUCCESS,
                raw_text=full_text,
            )
        except Exception as e:
            return ExtractionOutcome(
                status=ExtractionStatus.FAILED,
                failure_code=ExtractionFailureCode.CORRUPTED_FILE,
                failure_message=f"Corrupted or invalid PDF file: {str(e)}",
            )

    @classmethod
    def _extract_docx(cls, content: bytes) -> ExtractionOutcome:
        try:
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs).strip()

            if not full_text:
                return ExtractionOutcome(
                    status=ExtractionStatus.FAILED,
                    failure_code=ExtractionFailureCode.EMPTY_DOCUMENT,
                    failure_message="DOCX document contains no text.",
                )

            return ExtractionOutcome(
                status=ExtractionStatus.SUCCESS,
                raw_text=full_text,
            )
        except Exception as e:
            return ExtractionOutcome(
                status=ExtractionStatus.FAILED,
                failure_code=ExtractionFailureCode.CORRUPTED_FILE,
                failure_message=f"Corrupted or invalid DOCX file: {str(e)}",
            )
