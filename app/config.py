import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Default model to use for agents
DEFAULT_MODEL = "gemini-2.5-flash"

# Flag to require human verification for high severity tickets
REQUIRE_HUMAN_APPROVAL = os.getenv("REQUIRE_HUMAN_APPROVAL", "True").lower() == "true"
