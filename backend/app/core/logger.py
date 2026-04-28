import os
import sys

from loguru import logger

# remove the default Loguru handler
logger.remove()

# If we are in production, output strict JSON for the SIEM
if os.getenv("ENVIRONMENT") == "production":
    logger.add(sys.stdout, serialize=True)
else:
    # If we are in local development, output human-friendly, colour-coded logs
    logger.add(sys.stdout, colorize=True)
