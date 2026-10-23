"""
Backward-compatibility bridge for app.modules.production.dispatch_service.
All implementation is now cleanly organized in app.modules.production.dispatch package.
"""

from app.modules.production.dispatch import DispatchService, IcsError, dispatch_service

__all__ = ["DispatchService", "dispatch_service", "IcsError"]
