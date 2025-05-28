import requests
from django.conf import settings
from typing import Dict, List
import logging

logger = logging.getLogger('agent.payments')

class TVPaymentService:
    @staticmethod
    def get_available_packages() -> Dict:
        """Fetch available TV packages from NestJS"""
        try:
            logger.debug("Fetching packages from http://localhost:3000/tv-subscriptions")
            
            response = requests.get(
                "http://localhost:3000/tv-subscriptions",
                timeout=5
            )
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            
            response.raise_for_status()
            packages = response.json()
            
            if not isinstance(packages, list):
                logger.error(f"Expected list but got: {type(packages)}")
                return {"status": "error", "message": "Invalid data format"}
            
            return {
                "status": "success",
                "packages": [
                    {
                        "id": pkg["id"],
                        "name": pkg["name"],
                        "price": pkg["price"],
                        "service": pkg["service"]["name"]
                    }
                    for pkg in packages
                ]
            }
            
        except requests.exceptions.Timeout:
            logger.error("Request to NestJS timed out")
            return {"status": "error", "message": "Service timeout"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"status": "error", "message": "Service unavailable"}
            
        except ValueError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return {"status": "error", "message": "Invalid response"}
            
        except KeyError as e:
            logger.error(f"Missing expected field in response: {str(e)}")
            return {"status": "error", "message": "Invalid package data"}

    @staticmethod
    def process_subscription(account_number: str, package_id: int) -> Dict:
        """Process TV subscription payment with payment gateway"""
        url = "http://localhost:3000/tv-subscriptions/subscribe"
        payload = {
            "packageId": package_id,
            "accountNumber": account_number
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    'accept': '*/*',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Ensure consistent response format
            if "summary" not in data:
                data["summary"] = {
                    "transactionDate": time.strftime("%m/%d/%Y"),
                    "transactionTime": time.strftime("%I:%M:%S %p"),
                    "tvPackage": f"Package {package_id}",
                    "accountNumber": account_number,
                    "amount": 0, 
                    "tx_ref": data.get("transactionRef", "")
                }
            return data
            
        except requests.RequestException as e:
            logger.error(f"Subscription failed: {str(e)}")
            return {
                "status": "error",
                "message": "Payment service unavailable"
            }

    @staticmethod
    def check_payment_status(reference_id: str) -> Dict:
        """Check payment processing status"""
        url = f"http://localhost:3000/tv-subscriptions/status/{reference_id}"
        try:
            response = requests.get(
                url,
                headers={'accept': 'application/json'},
                timeout=5
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Status check failed: {str(e)}")
            return {
                "status": "error",
                "message": "Status service unavailable"
            }