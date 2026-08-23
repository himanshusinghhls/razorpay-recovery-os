"""
Backward-compatible re-export.

The canonical RecoveryAuthorization now lives in
application.recovery.service to avoid the previous duplication.
"""

from application.recovery.service import RecoveryAuthorization

__all__ = ["RecoveryAuthorization"]
