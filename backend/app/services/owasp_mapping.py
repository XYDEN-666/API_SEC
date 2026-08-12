"""OWASP API Security Top 10 category mapping (single source of truth).

Edition verification
--------------------
The current OWASP API Security Top 10 edition is **2023** (API1:2023 through
API10:2023) -- see https://owasp.org/API-Security/. The API-specific list was
last revised in 2023; the 2025/2026 "Top 10" updates apply to the general
web-application list, not the API list. Category identifiers therefore follow
the ``apiX:2023`` convention so persisted findings stay tied to a specific
edition.

Injection adjacency for SQLi
----------------------------
Injection (API8:2019) was removed as a standalone category in the 2023
revision. OWASP's own 2023 series records that injection risks were subsumed
into **API10:2023 (Unsafe Consumption of APIs)**, so the SQLi scanner maps
there rather than to a pre-2023 identifier or a made-up out-of-list code.
"""

OWASP_API_TOP_10_2023: dict[str, str] = {
    # Broken Object Level Authorization -- multi-identity replay detects
    # access-control anomalies where an object is reachable by a
    # lower-privileged identity.
    "idor_bola": "api1:2023",
    # Broken Authentication -- JWT configuration weaknesses (alg:none,
    # missing exp, weak signing secrets).
    "jwt": "api2:2023",
    # Security Misconfiguration -- missing/misconfigured security headers,
    # overly permissive CORS, and unexpectedly enabled HTTP methods.
    "headers": "api8:2023",
    "cors": "api8:2023",
    "http_methods": "api8:2023",
    # Unsafe Consumption of APIs -- injection (SQLi) is no longer its own
    # category in the 2023 edition; it was subsumed into API10:2023.
    "sqli_indicators": "api10:2023",
}


def category_for_scanner(scanner_name: str) -> str:
    """Return the OWASP API Top 10 (2023) category for a scanner name.

    Raises:
        ValueError: If the scanner name has no registered category. This is
            deliberate: a finding must never persist without a category, so
            unregistered scanners fail loudly instead of silently writing a
            null/invalid row.
    """
    try:
        return OWASP_API_TOP_10_2023[scanner_name]
    except KeyError:
        raise ValueError(
            f"No OWASP API Top 10 category registered for scanner "
            f"{scanner_name!r}"
        ) from None
