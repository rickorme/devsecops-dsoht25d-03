import sys

from logtail import LogtailHandler
from loguru import logger

from app.core.config import settings

# remove the default Loguru handler
logger.remove()

# 2. Keep your existing Console/Stdout handler (for local dev & Railway's raw logs)
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    serialize=True # Keeps your ECS JSON format!
)

# 3. THE MAGIC: Add Better Stack (Logtail) Handler
if settings.BETTER_STACK_TOKEN:
    # Initialize the Better Stack background sender
    logtail_handler = LogtailHandler(source_token=settings.BETTER_STACK_TOKEN)

    # Plug it directly into loguru
    logger.add(
        logtail_handler,
        level="INFO",
        serialize=True, # Ensures all your custom ECS fields (source.ip, etc) are sent
        enqueue=True    # Runs in a background thread so it never slows down FastAPI!
    )


# # If we are in production, output strict JSON for the SIEM
# if os.getenv("ENVIRONMENT") == "production":
#     logger.add(sys.stdout, serialize=True)
# else:
#     # If we are in local development, output human-friendly, colour-coded logs
#     logger.add(sys.stdout, colorize=True)
