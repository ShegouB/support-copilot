import re

# Regular expressions for common PII
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
IP_REGEX = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

# Prompts or injection keywords that should be flagged
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "system override",
    "you are now a dev",
    "you must ignore your instructions",
    "bypass safety",
]

def mask_pii(text: str) -> str:
    """Masks email addresses, phone numbers, and IP addresses in the input text."""
    if not text:
        return ""
    
    # Mask email
    masked = EMAIL_REGEX.sub("[EMAIL_MASKED]", text)
    # Mask phone numbers
    masked = PHONE_REGEX.sub("[PHONE_MASKED]", masked)
    # Mask IP addresses
    masked = IP_REGEX.sub("[IP_MASKED]", masked)
    
    return masked

def sanitize_input(text: str) -> str:
    """Sanitizes text and checks for potential prompt injection attempts.
    
    Raises:
        ValueError: If a known prompt injection pattern is detected.
    """
    if not text:
        return ""
        
    lower_text = text.lower()
    for kw in INJECTION_KEYWORDS:
        if kw in lower_text:
            raise ValueError(f"Security Alert: Blocked potential prompt injection attempt (keyword: '{kw}')")
            
    return text
