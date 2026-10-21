"""
AgroGuard Firestore Service Layer (Repository Abstraction)
===========================================================
Provides clean, modular repository methods for interacting with Google Cloud Firestore.
Features:
- Safe initialization verifying credentials and project settings.
- Cloud Firestore integration when FIREBASE_CREDENTIALS_PATH is provided.
- High-fidelity in-memory Firestore repository for local testing and development
  when cloud credentials are not yet supplied, avoiding spurious network failures.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import Config
from services.firestore_models import (
    generate_id,
    validate_farmer,
    validate_farm,
    validate_device,
    validate_sensor_reading,
    validate_farm_health,
    validate_advisory,
    validate_alert,
    validate_pump_event,
    ModelValidationError
)

class FirestoreService:
    """Modular service layer encapsulating all Firestore collection operations."""

    def __init__(self):
        self.client = None
        self.mode = "uninitialized"
        self.error_message = None
        
        # Local in-memory repository store (indexed by collection name -> doc_id -> doc)
        self._memory_store = {
            "farmers": {},
            "farms": {},
            "devices": {},
            "sensor_readings": {},
            "farm_health": {},
            "advisories": {},
            "alerts": {},
            "pump_events": {}
        }

        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initializes Firebase Admin SDK or sets up the development repository."""
        cred_path = Config.FIREBASE_CREDENTIALS_PATH

        if cred_path and os.path.exists(cred_path):
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if not firebase_admin._apps:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': Config.FIREBASE_PROJECT_ID
                    })
                
                self.client = firestore.client()
                self.mode = "firestore_cloud"
                print(f"[FIREBASE] Successfully initialized Google Cloud Firestore with credentials from: {cred_path}")
                return
            except Exception as e:
                self.error_message = str(e)
                print(f"[FIREBASE WARNING] Failed to initialize cloud Firestore client: {e}")

        # Check if Firestore Emulator is configured
        if Config.FIRESTORE_EMULATOR_HOST:
            try:
                import firebase_admin
                from firebase_admin import firestore
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(options={'projectId': Config.FIREBASE_PROJECT_ID})
                self.client = firestore.client()
                self.mode = "firestore_emulator"
                print(f"[FIREBASE] Connected to Firestore Emulator at {Config.FIRESTORE_EMULATOR_HOST}")
                return
            except Exception as e:
                print(f"[FIREBASE WARNING] Emulator connection failed: {e}")

        # Development / Test Mode: High-Fidelity in-memory repository
        self.mode = "in_memory_repository"
        print("[FIREBASE INFO] Firebase credentials not configured. Running in high-fidelity in-memory repository mode.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the health, connection mode, and record counts across all collections."""
        counts = {col: len(docs) for col, docs in self._memory_store.items()}
        return {
            "status": "healthy",
            "initialized": True,
            "mode": self.mode,
            "project_id": Config.FIREBASE_PROJECT_ID,
            "credentials_configured": bool(Config.FIREBASE_CREDENTIALS_PATH and os.path.exists(Config.FIREBASE_CREDENTIALS_PATH)),
            "collections_tracked": list(self._memory_store.keys()),
            "collections": counts,
            "record_counts": counts,
            "error": self.error_message
        }

    # -------------------------------------------------------------------------
    # 1. FARMERS COLLECTION
    # -------------------------------------------------------------------------
    def save_farmer(self, data: Dict[str, Any], farmer_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farmer(data)
        doc_id = farmer_id or clean.get("farmer_id") or generate_id("farmer_")
        clean["farmer_id"] = doc_id
        clean["farmerId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("farmers").document(doc_id).set(clean)
        self._memory_store["farmers"][doc_id] = clean
        return clean

    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            doc = self.client.collection("farmers").document(farmer_id).get()
            return doc.to_dict() if doc.exists else None
        return self._memory_store["farmers"].get(farmer_id)

    # -------------------------------------------------------------------------
    # 2. FARMS COLLECTION
    # -------------------------------------------------------------------------
    def save_farm(self, data: Dict[str, Any], farm_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm(data)
        doc_id = farm_id or clean.get("farm_id") or generate_id("farm_")
        clean["farm_id"] = doc_id
        clean["farmId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("farms").document(doc_id).set(clean)
        self._memory_store["farms"][doc_id] = clean
        return clean

    def get_farm(self, farm_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            doc = self.client.collection("farms").document(farm_id).get()
            return doc.to_dict() if doc.exists else None
        return self._memory_store["farms"].get(farm_id)

    def get_farms(self, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            query = self.client.collection("farms")
            if farmer_id:
                query = query.where("farmer_id", "==", farmer_id)
            return [doc.to_dict() for doc in query.stream()]
        
        docs = list(self._memory_store["farms"].values())
        if farmer_id:
            docs = [d for d in docs if d.get("farmer_id") == farmer_id or d.get("farmerId") == farmer_id]
        return docs

    # -------------------------------------------------------------------------
    # 3. DEVICES COLLECTION
    # -------------------------------------------------------------------------
    def register_device(self, data: Dict[str, Any], device_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_device(data)
        doc_id = device_id or clean.get("device_id") or generate_id("device_")
        clean["device_id"] = doc_id
        clean["deviceId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("devices").document(doc_id).set(clean)
        self._memory_store["devices"][doc_id] = clean
        return clean

    def get_devices(self, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            query = self.client.collection("devices")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            return [doc.to_dict() for doc in query.stream()]
        
        docs = list(self._memory_store["devices"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        return docs

    # -------------------------------------------------------------------------
    # 4. SENSOR READINGS COLLECTION
    # -------------------------------------------------------------------------
    def save_sensor_reading(self, data: Dict[str, Any], reading_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_sensor_reading(data)
        doc_id = reading_id or clean.get("reading_id") or generate_id("read_")
        clean["reading_id"] = doc_id
        clean["readingId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("sensor_readings").document(doc_id).set(clean)
        self._memory_store["sensor_readings"][doc_id] = clean
        return clean

    def get_recent_sensor_readings(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            from firebase_admin import firestore
            query = self.client.collection("sensor_readings")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            return [doc.to_dict() for doc in query.stream()]

        docs = list(self._memory_store["sensor_readings"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    # -------------------------------------------------------------------------
    # 5. FARM HEALTH (AFHI) COLLECTION
    # -------------------------------------------------------------------------
    def save_farm_health(self, data: Dict[str, Any], health_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm_health(data)
        doc_id = health_id or clean.get("health_id") or generate_id("afhi_")
        clean["health_id"] = doc_id
        clean["healthId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("farm_health").document(doc_id).set(clean)
        self._memory_store["farm_health"][doc_id] = clean
        return clean

    def get_farm_health_history(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            from firebase_admin import firestore
            query = self.client.collection("farm_health")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            return [doc.to_dict() for doc in query.stream()]

        docs = list(self._memory_store["farm_health"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    # -------------------------------------------------------------------------
    # 6. ADVISORIES (CAII + SPAE) COLLECTION
    # -------------------------------------------------------------------------
    def save_advisory(self, data: Dict[str, Any], advisory_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_advisory(data)
        doc_id = advisory_id or clean.get("advisory_id") or generate_id("adv_")
        clean["advisory_id"] = doc_id
        clean["advisoryId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("advisories").document(doc_id).set(clean)
        self._memory_store["advisories"][doc_id] = clean
        return clean

    def get_recent_advisories(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            from firebase_admin import firestore
            query = self.client.collection("advisories")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            return [doc.to_dict() for doc in query.stream()]

        docs = list(self._memory_store["advisories"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    # -------------------------------------------------------------------------
    # 7. ALERTS COLLECTION
    # -------------------------------------------------------------------------
    def create_alert(self, data: Dict[str, Any], alert_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_alert(data)
        doc_id = alert_id or clean.get("alert_id") or generate_id("alert_")
        clean["alert_id"] = doc_id
        clean["alertId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("alerts").document(doc_id).set(clean)
        self._memory_store["alerts"][doc_id] = clean
        return clean

    def get_recent_alerts(self, farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            from firebase_admin import firestore
            query = self.client.collection("alerts")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            if status:
                query = query.where("status", "==", status)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            return [doc.to_dict() for doc in query.stream()]

        docs = list(self._memory_store["alerts"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        if status:
            docs = [d for d in docs if d.get("status") == status]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    # -------------------------------------------------------------------------
    # 8. PUMP ACTUATOR EVENTS COLLECTION
    # -------------------------------------------------------------------------
    def record_pump_event(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_pump_event(data)
        doc_id = event_id or clean.get("event_id") or generate_id("event_")
        clean["event_id"] = doc_id
        clean["eventId"] = doc_id

        if self.mode == "firestore_cloud" and self.client:
            self.client.collection("pump_events").document(doc_id).set(clean)
        self._memory_store["pump_events"][doc_id] = clean
        return clean

    def get_pump_events(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if self.mode == "firestore_cloud" and self.client:
            from firebase_admin import firestore
            query = self.client.collection("pump_events")
            if farm_id:
                query = query.where("farm_id", "==", farm_id)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            return [doc.to_dict() for doc in query.stream()]

        docs = list(self._memory_store["pump_events"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

# Singleton Service Instance
firestore_service = FirestoreService()
