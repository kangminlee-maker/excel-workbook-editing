from __future__ import annotations

from dataclasses import dataclass


class DwdError(ValueError):
    """Raised when the DWD subject cannot be selected safely."""


@dataclass(frozen=True)
class DwdContext:
    service_account_email: str
    subject: str
    scopes: tuple[str, ...]


def select_subject(verified_identity: dict[str, object]) -> str:
    subject = verified_identity.get("subject") or verified_identity.get("principal")
    if not isinstance(subject, str) or "@" not in subject:
        raise DwdError("verified user principal is required for DWD subject")
    return subject.lower()


def build_dwd_context(
    *,
    service_account_email: str,
    verified_identity: dict[str, object],
    scopes: tuple[str, ...],
) -> DwdContext:
    if not service_account_email or "@" not in service_account_email:
        raise DwdError("service account email is required")
    if not scopes:
        raise DwdError("at least one DWD scope is required")
    return DwdContext(
        service_account_email=service_account_email,
        subject=select_subject(verified_identity),
        scopes=tuple(scopes),
    )
