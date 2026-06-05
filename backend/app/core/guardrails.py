import re

class PIIProtector:
    @staticmethod
    def mask_pii(text: str) -> str:
        # Simple regex-based masking for emails, phones
        # In full production, use Presidio or similar
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        
        masked = re.sub(email_pattern, "[EMAIL_HIDDEN]", text)
        masked = re.sub(phone_pattern, "[PHONE_HIDDEN]", masked)
        
        return masked

    @staticmethod
    def validate_content(text: str) -> bool:
        # Simple toxicity/injection check
        blacklist = ["DELETE FROM", "DROP TABLE", "<script>", "ignore previous instructions"]
        for item in blacklist:
            if item.lower() in text.lower():
                return False
        return True
