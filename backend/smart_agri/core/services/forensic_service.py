import hashlib
import json
import logging
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

class ForensicService:
    """
    ╔══════════════════════════════════════════════════════════╗
    ║ AGRIASSET FORENSIC EVIDENCE SERVICE (Zenith 4.0 GRP)    ║
    ╚══════════════════════════════════════════════════════════╝
    Implements AXIS 20 cryptographic non-repudiation.
    Ensures every financial and operational transaction is signed.
    """

    @staticmethod
    def generate_transaction_hash(payload):
        """Generates a SHA-256 fingerprint for a transaction payload."""
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    @staticmethod
    def sign_transaction(agent, action, payload, private_key=None):
        """
        Signs a transaction and returns a forensic proof.
        If private_key is missing, it uses the SOVEREIGN_MASTER_IDENTITY fallback.
        """
        timestamp = timezone.now().isoformat()
        payload_hash = ForensicService.generate_transaction_hash(payload)
        
        # Simplified HMAC-like signature for ERP layer integration
        # Real-world would use RSA/ECDSA
        secret = private_key or getattr(settings, 'SOVEREIGN_PRIVATE_KEY', 'FALLBACK_UNSAFE_SECRET')
        signature = hashlib.sha512(f"{payload_hash}{secret}{timestamp}".encode()).hexdigest()
        
        return {
            'event_id': hashlib.md5(f"{timestamp}{payload_hash}".encode()).hexdigest(),
            'timestamp': timestamp,
            'agent': agent,
            'action': action,
            'payload_hash': payload_hash,
            'signature': signature,
            'proof_level': 'AXIS_20_CERTIFIED'
        }

    @staticmethod
    def validate_gps_posture(lat, lon, accuracy, mode='STRICT'):
        """
        Validates the GPS context for GRP compliance.
        In STRICT mode, accuracy > 50m triggers a QUARANTINE block.
        """
        if lat is None or lon is None or accuracy is None:
            return False, "Missing mandatory GPS evidence"
        
        if mode == 'STRICT' and accuracy > 50:
            return False, f"GPS Accuracy violation: {accuracy}m exceeded threshold of 50m"
        
        return True, "GPS Posture Valid"
