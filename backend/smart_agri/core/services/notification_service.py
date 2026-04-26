import logging
import os
import requests
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)

class LocalNotificationGateway:
    """
    [AGRI-GUARDIAN] Local SMS/WhatsApp Gateway Stub
    Used for dispatching high-priority financial alerts (e.g., proactive Petty Cash limit breaches)
    to Farm Finance Managers, instead of just silent 403 blocks.
    """
    
    GATEWAY_URL = os.environ.get("AGRIASSET_SMS_GATEWAY_URL", "http://localhost:8080/v1/messages")
    API_KEY = os.environ.get("AGRIASSET_SMS_GATEWAY_KEY", "dummy-key")
    IS_ENABLED = os.environ.get("AGRIASSET_SMS_ENABLED", "0").lower() in ("1", "true", "yes")

    @classmethod
    def send_sms(cls, phone_number: str, message: str) -> bool:
        """
        Stub to send SMS via local gateway.
        """
        if not cls.IS_ENABLED:
            logger.info("SMS Notification skipped (AGRIASSET_SMS_ENABLED is false). Message: %s", message)
            return True
            
        if not phone_number:
            logger.warning("Attempted to send SMS but no phone number provided.")
            return False

        payload = {
            "to": phone_number,
            "body": message,
            "type": "sms"
        }
        
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            # Short timeout to prevent blocking financial operations
            response = requests.post(cls.GATEWAY_URL, json=payload, headers=headers, timeout=3.0)
            if response.status_code in (200, 201, 202):
                logger.info("SMS successfully dispatched to %s", phone_number)
                return True
            else:
                logger.error("SMS Gateway error: %s - %s", response.status_code, response.text)
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error("SMS Gateway connection failed: %s", e)
            # Failsafe: return False but don't crash the calling mutating transaction.
            return False

    @classmethod
    def notify_farm_finance_manager(cls, farm, message: str) -> bool:
        """
        Locates the Farm Finance Manager(s) for the given farm and attempts to SMS them.
        """
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        from smart_agri.finance.roles import ROLES

        finance_managers = FarmFinanceAuthorityService.get_users_with_role(farm=farm, role_name=ROLES.FARM_FINANCE_MANAGER)
        
        success_count = 0
        for fm in finance_managers:
            # Assuming user model has a 'profile.phone_number' or 'phone_number' field
            phone = getattr(fm, 'phone_number', None)
            if hasattr(fm, 'profile') and not phone:
                phone = getattr(fm.profile, 'phone_number', None)
                
            if phone:
                if cls.send_sms(phone, message):
                    success_count += 1
            else:
                logger.warning(f"Farm Finance Manager {fm.username} lacks a phone number. Cannot notify.")

        return success_count > 0

    @classmethod
    def notify_sector_finance_director(cls, farm, message: str) -> bool:
        """
        Locates the Sector Finance Director for the sector associated with the farm
        and attempts to SMS them regarding critical governance exceptions.
        """
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        from smart_agri.finance.roles import ROLES

        # Determine sector finance director from authority service logic
        # Usually lives in the 'Sector' level which farm is part of.
        directors = FarmFinanceAuthorityService.get_users_with_role(farm=farm, role_name=ROLES.SECTOR_FINANCE_DIRECTOR)
        
        success_count = 0
        for director in directors:
            phone = getattr(director, 'phone_number', None)
            if hasattr(director, 'profile') and not phone:
                phone = getattr(director.profile, 'phone_number', None)
                
            if phone:
                if cls.send_sms(phone, f"[CRITICAL GOVERNANCE] {message}"):
                    success_count += 1
            else:
                logger.warning(f"Sector Finance Director {director.username} lacks a phone number. Cannot notify.")

        return success_count > 0

