"""
AgroGuard Firestore Service Bridge
=================================
Seamlessly bridges legacy Firestore service calls to the unified AgroGuard Database Service,
ensuring 100% backward compatibility for existing routes, tests, and models.
"""
from .database import db_service, firestore_service
from .database.models import ModelValidationError

__all__ = ['db_service', 'firestore_service', 'ModelValidationError']
