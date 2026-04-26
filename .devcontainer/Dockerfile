# Base: Official Playwright Python image (Ubuntu 24.04 "Noble")
# This gives you Python 3.12+ and all browsers (Chromium, Firefox, WebKit) pre-installed.
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Avoid Python writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. Install System Tools & Node.js (Version 22 LTS is recommended for 2026 stability)
# We use the NodeSource setup you provided, updated to the current LTS.
RUN apt-get update && apt-get install -y \
    curl \
    git \
    make \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g newman \
    && rm -rf /var/lib/apt/lists/*

# 2. Install uv (The modern Python package manager)
# We copy the binary directly from the official image (safest/fastest method)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3. Create a non-root user 'vscode' (Best practice for Dev Containers)
# The playwright image uses root by default, so we create a user for VS Code.
# 3. Create or Update the non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN if id -u $USER_UID >/dev/null 2>&1; then \
        # Case A: User 1000 already exists (e.g. 'ubuntu'). Rename it to 'vscode'.
        EXISTING_USER=$(getent passwd $USER_UID | cut -d: -f1) && \
        usermod -l $USERNAME $EXISTING_USER && \
        groupmod -n $USERNAME $EXISTING_USER && \
        usermod -d /home/$USERNAME -m $USERNAME; \
    else \
        # Case B: User 1000 does not exist. Create it.
        groupadd --gid $USER_GID $USERNAME && \
        useradd --uid $USER_UID --gid $USER_GID -m $USERNAME; \
    fi \
    # Ensure workspace permissions
    && mkdir -p /workspace \
    && chown -R $USERNAME:$USERNAME /workspace

# Set default user
# USER $USERNAME
WORKDIR /workspace