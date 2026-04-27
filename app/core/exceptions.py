class LLMError(Exception):
    """Raised when the upstream LLM call fails."""


class CrawlerError(Exception):
    """Raised when a source's discover or fetch_pdf step fails non-recoverably."""


class StorageError(Exception):
    """Raised when MinIO upload/download fails non-recoverably."""


class ExtractionError(Exception):
    """Raised when LLM extraction fails to produce a valid response."""
