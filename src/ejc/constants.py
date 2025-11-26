"""Constants for the Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF)"""

# Validation Constants
MAX_TEXT_LENGTH = 50000  # Maximum input text length (DoS protection)
MIN_TEXT_LENGTH = 1      # Minimum input text length

# LLM API Constants
DEFAULT_MAX_TOKENS = 512  # Default max tokens for LLM responses
DEFAULT_SUMMARY_LENGTH = 80  # Default length for truncated summaries

# Retraining Constants
DEFAULT_BATCH_SIZE = 25  # Number of decisions before triggering retraining
MIN_CONFIDENCE_FOR_RETRAINING = 0.8  # Minimum confidence to include in training

# Retry Constants
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts for API calls
RETRY_MIN_WAIT = 2      # Minimum wait time in seconds between retries
RETRY_MAX_WAIT = 10     # Maximum wait time in seconds between retries
RETRY_MULTIPLIER = 1    # Exponential backoff multiplier

# Precedent Constants
PRECEDENT_SIMILARITY_THRESHOLD = 0.55  # Threshold for semantic similarity

# Verdict Types
VERDICT_ALLOW = "ALLOW"
VERDICT_DENY = "DENY"
VERDICT_REVIEW = "REVIEW"
VERDICT_BLOCK = "BLOCK"
VERDICT_ERROR = "ERROR"

VALID_VERDICTS = {VERDICT_ALLOW, VERDICT_DENY, VERDICT_REVIEW, VERDICT_BLOCK, VERDICT_ERROR}

# Priority Levels
PRIORITY_OVERRIDE = "override"

# Default Configuration Values
DEFAULT_BLOCK_THRESHOLD = 0.5
DEFAULT_AMBIGUITY_THRESHOLD = 0.25
DEFAULT_MAX_PARALLEL_CALLS = 5
DEFAULT_DATA_PATH = "./eleanor_data"
DEFAULT_CONFIG_PATH = "config/global.yaml"
DEFAULT_DASHBOARD_PORT = 8049
DEFAULT_DB_URI = "sqlite:///eleanor_data/eleanor.db"
