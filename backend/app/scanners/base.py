"""Scanner interface: the contract every APIShield scanner implements.

Writing a new scanner
---------------------
A scanner is a class that inherits from :class:`BaseScanner` and implements
exactly one method: :meth:`BaseScanner.scan`. Everything else the platform
needs (orchestration, scheduling, finding persistence, report generation) is
handled outside the scanner.

Example:

    from app.models import Credential, Endpoint, Target
    from app.scanners.base import (
        BaseScanner,
        Confidence,
        Finding,
        Severity,
    )

    class HeaderScanner(BaseScanner):
        name = "headers"
        description = "Checks for missing security response headers."

        async def scan(self, target, endpoint, credentials):
            findings = []
            if endpoint is not None:
                # ... perform the HTTP request using target.base_url and
                # endpoint.path, attaching credentials if provided ...
                findings.append(
                    Finding(
                        title="Missing X-Content-Type-Options",
                        description=(
                            "The endpoint does not send the "
                            "X-Content-Type-Options header."
                        ),
                        severity=Severity.LOW,
                        evidence="GET /health returned no X-Content-Type-Options header",
                        owasp_category="api5:2023",
                        confidence=Confidence.HIGH,
                    )
                )
            return findings

Rules:

* Implement ``scan()`` only. Do not reach into orchestrator internals, session
  management, or persistence from inside a scanner.
* ``scan()`` is async, so scanners can perform real HTTP/network work.
* Return a list of :class:`Finding` (an empty list means "no issues found").
* Use the :class:`Severity` and :class:`Confidence` enums for those fields so
  downstream engines can sort and filter consistently.
* Use OWASP API Security Top 10 identifiers for ``owasp_category``. Prefer
  ``app.services.owasp_mapping.category_for_scanner()`` -- it is the single
  source of truth for the current (2023) edition's categories.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from app.models import Credential, Endpoint, Target


class Severity(Enum):
    """Severity of a finding, from informational to critical."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(Enum):
    """How sure the scanner is that the finding is a real issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Finding:
    """A single issue discovered by a scanner.

    Attributes:
        title: Short human-readable summary, e.g. "Missing X-Frame-Options".
        description: Longer explanation of the issue and why it matters.
        severity: One of :class:`Severity`.
        evidence: Concrete proof captured during the scan (response headers,
            status codes, request/response excerpts, etc.).
        owasp_category: OWASP API Security Top 10 identifier, e.g. "api5:2023".
        confidence: One of :class:`Confidence`.
    """

    title: str
    description: str
    severity: Severity
    evidence: str
    owasp_category: str
    confidence: Confidence


class BaseScanner(ABC):
    """Abstract base class for all APIShield scanners.

    Subclasses must set ``name`` and ``description`` and implement
    :meth:`scan`. See the module docstring for the full writing guide.
    """

    #: Unique identifier for the scanner, used in reports and findings.
    name: str = "base"
    #: Human-readable description of what the scanner checks.
    description: str = ""

    @abstractmethod
    async def scan(
        self,
        target: Target,
        endpoint: Endpoint | None,
        credentials: Credential | None,
    ) -> list[Finding]:
        """Scan a target or endpoint and return the findings.

        Args:
            target: The target being scanned. Always provided; use
                ``target.base_url`` as the base for HTTP requests.
            endpoint: The specific endpoint to scan, or ``None`` when the
                scanner operates at the target level (e.g. checking the
                whole API for missing security headers).
            credentials: Decrypted credentials (an internal value) to use for
                authenticated scanning, or ``None`` for unauthenticated scans.
                Never include the raw value in a finding's evidence.

        Returns:
            A list of :class:`Finding`; empty means no issues were found.
        """
        raise NotImplementedError
