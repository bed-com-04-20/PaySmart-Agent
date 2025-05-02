import re
import logging
import time
from typing import Dict, Optional, Tuple
from agent.infrastructure.nestjs_adapter.tv_payment import TVPaymentService

logger = logging.getLogger('agent.payments')

class TVPaymentHandler:
    
    @staticmethod
    def handle_payment_flow(user_message: str, session: Dict) -> str:
        """Main entry point for handling TV payment flow"""
        msg_lower = user_message.lower()
        
        # Check if user is asking to see packages
        if any(cmd in msg_lower for cmd in ["show packages", "list packages", "what packages"]):
            return TVPaymentHandler.list_available_packages()
            
        # Payment status check
        if session.get("processing_payment"):
            return TVPaymentHandler._check_payment_status(session)
            
        # Confirmation handling
        if session.get("awaiting_confirmation"):
            return TVPaymentHandler._handle_confirmation(user_message, session)
            
        # Package selection handling
        if any(word in msg_lower for word in ["package", "pkg", "plan", "select", "want"]):
            return TVPaymentHandler._process_package_selection(user_message, session)
            
        # Default response
        return ("📺 Welcome to TV Subscription Service!\n\n"
               "To see available packages, type 'show packages'\n"
               "To subscribe, type 'I want package [number] for account [your-account]'")

    @staticmethod
    def list_available_packages() -> str:
        """Display available packages"""
        result = TVPaymentService.get_available_packages()
        if result["status"] != "success":
            return "⚠️ Could not fetch packages. Please try again later."
        
        packages = result.get("packages", [])
        if not packages:
            return "No available packages at this time"
            
        package_list = []
        for pkg in sorted(packages, key=lambda x: x['id']):
            package_list.append(
                f"🔹 {pkg['id']}. {pkg['name']} ({pkg.get('service', 'Unknown')}) - MK{pkg['price']}/month"
            )
            
        return (
            "📺 Available TV Packages:\n\n" +
            "\n".join(package_list) +
            "\n\nTo subscribe, reply with:\n"
            "'I want package [number] for account [your-account-number]'"
        )

    @staticmethod
    def _process_package_selection(user_message: str, session: Dict) -> str:
        """Handle package selection"""
        package_id, account = TVPaymentHandler.extract_details(user_message)
        
        if not package_id:
            return ("⚠️ Please specify which package you want.\n"
                   "Example: 'I want package 3 for account TV-12345678'\n\n"
                   f"{TVPaymentHandler.list_available_packages()}")
                   
        if not account:
            return "⚠️ Please provide your TV account number to continue."
            
        if not TVPaymentHandler.validate_account_number(account):
            return "❌ Invalid account number format (8-20 alphanumeric characters with optional hyphens)"
            
        packages = TVPaymentService.get_available_packages().get("packages", [])
        selected_pkg = next((pkg for pkg in packages if pkg['id'] == package_id), None)
        
        if not selected_pkg:
            return (f"❌ Package {package_id} not found.\n\n"
                   f"{TVPaymentHandler.list_available_packages()}")
            
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
        
        return (
            f"📺 Confirm Subscription:\n\n"
            f"Service: {selected_pkg.get('service', 'Unknown')}\n"
            f"Package: {selected_pkg['name']} (ID: {package_id})\n"
            f"Price: MK{selected_pkg['price']} per month\n"
            f"Account: {account}\n\n"
            f"Type 'yes' to confirm and proceed to payment or 'no' to cancel"
        )

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
    def _check_payment_status(session: Dict) -> str:
        """Check payment status"""
        ref = session.get("payment_reference")
        if not ref:
            session.clear()
            return "⚠️ Missing payment reference. Please start over."
            
        result = TVPaymentService.check_payment_status(ref)
        
        if result.get("status") == "completed":
            session.clear()
            return (f"✅ Payment completed!\n\n"
                   f"Account: {result['accountNumber']}\n"
                   f"Package: {result['packageName']}\n"
                   f"Expires: {result.get('expiryDate', 'N/A')}")
                   
        elif result.get("status") == "failed":
            session.clear()
            return f"❌ Payment failed: {result.get('message', 'Unknown error')}"
            
        if time.time() - session.get("payment_start_time", 0) > 300:
            session.clear()
            return "⚠️ Payment timeout. Please contact support."
        return "⏳ Payment still processing. We'll notify you when complete."

    @staticmethod
    def _handle_confirmation(user_message: str, session: Dict) -> str:
        """Handle confirmation response and payment gateway integration"""
        if "yes" not in user_message.lower():
            session.clear()
            return "⚠️ Payment cancelled."
            
        params = session.get("payment_params")
        if not params:
            session.clear()
            return "⚠️ Session expired. Please start over."
            
        result = TVPaymentService.process_subscription(
            params["account_number"],
            params["package_id"]
        )
        
        if result.get("checkout_url"):
            session.clear()
            return (
                f"✅ Please proceed to payment:\n\n"
                f"Service: {params.get('service_name', 'Unknown')}\n"
                f"Package: {params['package_name']}\n"
                f"Account: {params['account_number']}\n"
                f"Amount: MK{params['package_price']}\n\n"
                f"👉 Payment Link: {result['checkout_url']}\n\n"
                f"Click the link above to complete your payment."
            )
        elif result.get("status") == "processing":
            session["processing_payment"] = True
            session["payment_reference"] = result["transactionRef"]
            session["payment_start_time"] = time.time()
            return "⏳ Processing your payment..."
        else:
            session.clear()
            return f"❌ Payment failed: {result.get('message', 'Unknown error')}"