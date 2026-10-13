import re
import unicodedata


class TextCleaner:
    """Cleans raw extracted text while preserving section boundaries and tokens."""

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize("NFKD", text)

        # Replace non-breaking spaces and tabs with standard space
        text = text.replace("\u00a0", " ").replace("\t", " ")

        # Remove control characters except newlines
        text = "".join(
            ch for ch in text
            if ch == "\n" or not unicodedata.category(ch).startswith("C")
        )

        # Normalize multiple spaces per line
        lines = [re.sub(r" +", " ", line).strip() for line in text.split("\n")]

        # Collapse excessive newlines (max 2 consecutive)
        cleaned_text = "\n".join(lines)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()

        return cleaned_text
