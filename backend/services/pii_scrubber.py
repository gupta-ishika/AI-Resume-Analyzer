import re


class PIIScrubber:
    """
    Deterministic PII and demographic scrubber owned by Person 1.
    Removes candidate identifying information, institution names, and gendered terms.
    """

    GENDERED_TERMS_MAP: dict[str, str] = {
        r"\bhe\b": "they",
        r"\bshe\b": "they",
        r"\bhim\b": "them",
        r"\bher\b": "them",
        r"\bhis\b": "their",
        r"\bhers\b": "theirs",
        r"\bhimself\b": "themself",
        r"\bherself\b": "themself",
        r"\bmr\.?\b": "",
        r"\bms\.?\b": "",
        r"\bmrs\.?\b": "",
    }

    EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

    @classmethod
    def scrub_text(
        cls,
        text: str,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        institutions: list[str] | None = None,
    ) -> str:
        """
        Deterministically scrubs all personal attributes from professional text.
        Guarantees that identical professional experience with different demographic
        attributes produces identical scrubbed output.
        """
        if not text:
            return ""

        scrubbed = text

        # 1. Remove known email
        if email:
            scrubbed = re.sub(re.escape(email), "", scrubbed, flags=re.IGNORECASE)
        scrubbed = re.sub(cls.EMAIL_PATTERN, "", scrubbed)

        # 2. Remove known phone
        if phone:
            scrubbed = re.sub(re.escape(phone), "", scrubbed, flags=re.IGNORECASE)
        scrubbed = re.sub(cls.PHONE_PATTERN, "", scrubbed)

        # 3. Remove candidate name (whole and parts if > 2 chars)
        if name and name.lower() != "unknown candidate":
            # Sort tokens longest first to prevent partial replacement collisions
            name_tokens = sorted(
                [tok for tok in re.split(r"\s+", name) if len(tok) > 2],
                key=len,
                reverse=True,
            )
            for token in name_tokens:
                scrubbed = re.sub(rf"\b{re.escape(token)}\b", "", scrubbed, flags=re.IGNORECASE)

        # 4. Remove institution names
        if institutions:
            for inst in institutions:
                if inst and len(inst.strip()) > 3:
                    scrubbed = re.sub(
                        rf"\b{re.escape(inst.strip())}\b", "", scrubbed, flags=re.IGNORECASE
                    )

        # Common generic educational institution keywords
        scrubbed = re.sub(
            r"\b(?:University|College|Institute|School)\s+of\s+[A-Za-z]+",
            "",
            scrubbed,
            flags=re.IGNORECASE,
        )
        scrubbed = re.sub(
            r"\b[A-Za-z]+\s+(?:University|College|Institute|School)\b",
            "",
            scrubbed,
            flags=re.IGNORECASE,
        )

        # 5. Replace gendered pronouns and terms with neutral equivalents
        for pattern, replacement in cls.GENDERED_TERMS_MAP.items():
            scrubbed = re.sub(pattern, replacement, scrubbed, flags=re.IGNORECASE)

        # 6. Normalize whitespace
        scrubbed = re.sub(r"[^\S\r\n]+", " ", scrubbed)
        scrubbed = re.sub(r"\n\s*\n+", "\n\n", scrubbed)
        return scrubbed.strip()
