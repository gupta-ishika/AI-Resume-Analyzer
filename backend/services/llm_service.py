import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger("llm_service")


class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMConnectionError(LLMError):
    """Raised when unable to connect to Ollama."""


class LLMTimeoutError(LLMError):
    """Raised when Ollama inference times out."""


class LLMResponseParseError(LLMError):
    """Raised when Ollama output cannot be parsed as JSON."""


class LLMService(ABC):
    """
    Abstract interface for LLM explanation generation (LLM-02).
    Ensures that Ollama or any alternative local/remote LLM can be substituted cleanly.
    """

    @abstractmethod
    def generate_explanation(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Generates a structured explanation dictionary from prompt inputs."""
        pass


class OllamaLLMService(LLMService):
    """
    Adapter for Ollama local LLM service (LLM-02).
    Communicates via Ollama's HTTP API (/api/generate) with structured JSON enforcement.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.EXPLANATION_TIMEOUT_SECONDS

    def generate_explanation(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.base_url}: {e}")
            raise LLMConnectionError(
                f"Could not connect to Ollama at {self.base_url}. Ensure Ollama service is running."
            ) from e
        except httpx.TimeoutException as e:
            logger.error(f"Ollama generation timed out after {self.timeout}s: {e}")
            raise LLMTimeoutError(
                f"Ollama explanation request timed out after {self.timeout} seconds."
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama returned HTTP error {e.response.status_code}: {e}")
            raise LLMError(f"Ollama returned HTTP {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Unexpected error communicating with Ollama: {e}")
            raise LLMError(f"Error calling Ollama: {str(e)}") from e

        raw_response = data.get("response", "")
        if not raw_response:
            raise LLMResponseParseError("Ollama returned an empty response body.")

        try:
            parsed = json.loads(raw_response)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed JSON root is not an object.")
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}\nRaw: {raw_response[:200]}")
            raise LLMResponseParseError(
                f"Failed to parse JSON explanation from Ollama: {str(e)}"
            ) from e


class MockLLMService(LLMService):
    """
    Test and development mock service providing deterministic or custom outputs.
    """

    def __init__(
        self,
        canned_response: dict[str, Any] | None = None,
        should_fail: bool = False,
        failure_exc: Exception | None = None,
    ):
        self.canned_response = canned_response or {
            "strengths": [
                "Strong demonstrated proficiency in Python and FastAPI backend development."
            ],
            "gaps": ["Lacks hands-on experience with Docker and Kubernetes infrastructure."],
            "experience_alignment": (
                "Candidate has 3 years of backend experience directly matching the role's "
                "core architectural requirements."
            ),
            "assessment": (
                "Highly viable candidate with strong required skill coverage and suitable "
                "experience."
            ),
        }
        self.should_fail = should_fail
        self.failure_exc = failure_exc or LLMConnectionError("Simulated Ollama connection failure")

    def generate_explanation(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        if self.should_fail:
            raise self.failure_exc
        return self.canned_response


# Global default adapter
default_llm_service: LLMService = OllamaLLMService()
