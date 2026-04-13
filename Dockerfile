FROM python:3.12-slim

# Install supervisord, curl, ca-certificates
# Note: Java not needed — we use the signal-cli native binary (self-contained)
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install signal-cli (native binary — no JVM needed)
ARG SIGNAL_CLI_VERSION=0.13.4
RUN curl -fsSL "https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/signal-cli-${SIGNAL_CLI_VERSION}-Linux-native.tar.gz" \
    | tar -xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/signal-cli

WORKDIR /app

# Install Python deps
COPY server/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY server/ ./server/
COPY context/ ./context/
COPY reminders.yaml .
COPY supervisord.conf .
COPY entrypoint.sh .

RUN mkdir -p /data/signal-cli /data/notes

ENTRYPOINT ["/app/entrypoint.sh"]
