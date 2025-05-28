import re
import logging
import time
from typing import Dict, Optional, Tuple, Union
from agent.infrastructure.nestjs_adapter.tv_payment import TVPaymentService

logger = logging.getLogger('agent.payments')

class TVPaymentHandler:
    
    @staticmethod
    def handle_payment_flow(user_message: str, session: Dict) -> Union[str, Dict]:
        """Main entry point for handling TV payment flow"""
        msg_lower = user_message.lower()
        
        if any(cmd in msg_lower for cmd in ["show packages", "list packages", "what packages"]):
            return TVPaymentHandler.list_available_packages()
            
        if session.get("processing_payment"):
            return TVPaymentHandler._check_payment_status(session)
            
        if session.get("awaiting_confirmation"):
            return TVPaymentHandler._handle_confirmation(user_message, session)
            
        if any(word in msg_lower for word in ["package", "pkg", "plan", "select", "want"]):
            return TVPaymentHandler._process_package_selection(user_message, session)
            
        return {
            "message": ("📺 Welcome to TV Subscription Service!\n\n"
                       "To see available packages, type 'show packages'\n"
                       "To subscribe, type 'I want package [number] for account [your-account]'"),
            "type": "info"
        }

    @staticmethod
    def list_available_packages() -> Dict:
        """Display available packages"""
        result = TVPaymentService.get_available_packages()
        if result["status"] != "success":
            return {
                "message": "⚠️ Could not fetch packages. Please try again later.",
                "type": "error"
            }
        
        packages = result.get("packages", [])
        if not packages:
            return {
                "message": "No available packages at this time",
                "type": "info"
            }
            
        package_list = []
        for pkg in sorted(packages, key=lambda x: x['id']):
            package_list.append(
                f"🔹 {pkg['id']}. {pkg['name']} ({pkg.get('service', 'Unknown')}) - MK{pkg['price']}/month"
            )
            
        return {
            "message": (
                "📺 Available TV Packages:\n\n" +
                "\n".join(package_list) +
                "\n\nTo subscribe, reply with:\n"
                "'I want package [number] for account [your-account-number]'"),
            "type": "packages",
            "packages": packages
        }

    @staticmethod
    def _process_package_selection(user_message: str, session: Dict) -> Dict:
        """Handle package selection"""
        package_id, account = TVPaymentHandler.extract_details(user_message)
        
        if not package_id:
            packages_response = TVPaymentHandler.list_available_packages()
            return {
                "message": ("⚠️ Please specify which package you want.\n"
                           "Example: 'I want package 3 for account TV-12345678'\n\n" +
                           packages_response["message"]),
                "type": "error"
            }
                   
        if not account:
            return {
                "message": "⚠️ Please provide your TV account number to continue.",
                "type": "error"
            }
            
        if not TVPaymentHandler.validate_account_number(account):
            return {
                "message": "❌ Invalid account number format (8-20 alphanumeric characters with optional hyphens)",
                "type": "error"
            }
            
        packages = TVPaymentService.get_available_packages().get("packages", [])
        selected_pkg = next((pkg for pkg in packages if pkg['id'] == package_id), None)
        
        if not selected_pkg:
            packages_response = TVPaymentHandler.list_available_packages()
            return {
                "message": f"❌ Package {package_id} not found.\n\n" + packages_response["message"],
                "type": "error"
            }
            
        session.update({
            "payment_params": {
                "package_id": package_id,
                "package_name": selected_pkg['name'],
                "package_price": selected_pkg['price'],
                "service_name": selected_pkg.get('service', 'Unknown'),
                "account_number": account
            },
            "awaiting_confirmation": True
        })
        
        return {
            "message": (
                f"📺 Confirm Subscription:\n\n"
                f"Service: {selected_pkg.get('service', 'Unknown')}\n"
                f"Package: {selected_pkg['name']} (ID: {package_id})\n"
                f"Price: MK{selected_pkg['price']} per month\n"
                f"Account: {account}"
            ),
            "type": "confirmation",
            "details": {
                "service": selected_pkg.get('service', 'Unknown'),
                "package": selected_pkg['name'],
                "price": selected_pkg['price'],
                "account": account
            }
        }

    @staticmethod
    def validate_account_number(account: str) -> bool:
        """Validate account number format"""
        return bool(re.fullmatch(r'^[A-Z0-9-]{8,20}$', account))

    @staticmethod
    def extract_details(message: str) -> Tuple[Optional[int], Optional[str]]:
        """Extract package ID and account number"""
        try:
            pkg_match = re.search(r'(?:package|pkg|plan)\s*(\d+)', message, re.I)
            acct_match = re.search(r'(?:account|acct|number)\s*([A-Z0-9-]+)', message, re.I)
            return (
                int(pkg_match.group(1)) if pkg_match else None,
                acct_match.group(1) if acct_match else None
            )
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return None, None

    @staticmethod
    def _check_payment_status(session: Dict) -> Dict:
        """Check payment status"""
        ref = session.get("payment_reference")
        if not ref:
            session.clear()
            return {
                "message": "⚠️ Missing payment reference. Please start over.",
                "type": "error"
            }
            
        result = TVPaymentService.check_payment_status(ref)
        
        if result.get("status") == "completed":
            session.clear()
            return {
                "message": (f"✅ Payment completed!\n\n"
                           f"Account: {result['accountNumber']}\n"
                           f"Package: {result['packageName']}\n"
                           f"Expires: {result.get('expiryDate', 'N/A')}"),
                "type": "success",
                "payment_status": "completed"
            }
                   
        elif result.get("status") == "failed":
            session.clear()
            return {
                "message": f"❌ Payment failed: {result.get('message', 'Unknown error')}",
                "type": "error",
                "payment_status": "failed"
            }
            
        if time.time() - session.get("payment_start_time", 0) > 300:
            session.clear()
            return {
                "message": "⚠️ Payment timeout. Please contact support.",
                "type": "error"
            }
            
        return {
            "message": "⏳ Payment still processing. We'll notify you when complete.",
            "type": "info",
            "payment_status": "processing"
        }

    @staticmethod
    def _handle_confirmation(user_message: str, session: Dict) -> Dict:
        logger.debug(f"INCOMING SESSION STATE: {session}")
        """Handle confirmation response and payment gateway integration"""
        logger.info(f"✅ Processing confirmation: {user_message}")
        
        # Clear session only on explicit cancellation
        if "yes" not in user_message.lower():
            logger.warning("⏹️ User cancelled payment")
            session.clear()
            return {
                "message": "⚠️ Payment cancelled.",
                "type": "info"
            }
            
        # Validate session state
        params = session.get("payment_params")
        if not params:
            logger.error("❌ Missing payment parameters in session")
            session.clear()
            return {
                "message": "⚠️ Session expired. Please start over.",
                "type": "error"
            }
        
        try:
            # Process payment with preserved session context
            logger.debug("🚀 Initiating payment processing")
            result = TVPaymentService.process_subscription(
                params["account_number"],
                params["package_id"]
            )
            logger.debug(f"📄 Payment service response: {result}")

            # Handle successful payment URL generation
            if result.get("checkout_url"):
                logger.info(f"🔗 Payment URL received: {result['checkout_url']}")
                
                # Update session state instead of clearing
                session["active_payment"] = {
                    "url": result['checkout_url'],
                    "reference": result.get('transactionRef'),
                    "timestamp": time.time()
                }
                session.pop("awaiting_confirmation", None)  # Remove confirmation flag
                
                return {
                    "message": "✅ Please proceed to payment",
                    "type": "payment",
                    "payment_url": result['checkout_url'],
                    "details": {
                        "service": params.get('service_name', 'Unknown'),
                        "package": params['package_name'],
                        "account": params['account_number'],
                        "amount": params['package_price'],
                        "reference": result.get('transactionRef')
                    }
                }

            # Handle processing status
            if result.get("status") == "processing":
                logger.info("⏳ Payment processing initiated")
                session["processing_payment"] = True
                session["payment_reference"] = result.get("transactionRef")
                session["payment_start_time"] = time.time()
                return {
                    "message": "⏳ Processing your payment...",
                    "type": "info",
                    "payment_status": "processing",
                    "payment_reference": result.get("transactionRef")
                }

            # Handle errors
            logger.error(f"💥 Payment failed: {result.get('message')}")
            session.clear()
            return {
                "message": f"❌ Payment failed: {result.get('message', 'Unknown error')}",
                "type": "error"
            }

        except Exception as e:
            logger.error(f"🔥 Critical payment error: {str(e)}")
            session.clear()
            return {
                "message": "❌ Payment system error. Please try again later.",
                "type": "error"
            }