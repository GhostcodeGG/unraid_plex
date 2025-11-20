FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY plex_monitor.py .

# Create data directory
RUN mkdir -p /app/data

# Set up cron for scheduled monitoring
RUN apt-get update && \
    apt-get install -y cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Default schedule: run every 6 hours
ENV CRON_SCHEDULE="0 */6 * * *"

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "$CRON_SCHEDULE cd /app && /usr/local/bin/python /app/plex_monitor.py >> /var/log/cron.log 2>&1" > /etc/cron.d/plex-monitor\n\
chmod 0644 /etc/cron.d/plex-monitor\n\
crontab /etc/cron.d/plex-monitor\n\
touch /var/log/cron.log\n\
echo "Starting Plex Monitor with schedule: $CRON_SCHEDULE"\n\
echo "Running initial monitoring..."\n\
cd /app && /usr/local/bin/python /app/plex_monitor.py\n\
echo "Initial monitoring complete. Starting cron daemon..."\n\
cron && tail -f /var/log/cron.log /app/plex_monitor.log' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
