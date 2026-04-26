#!/bin/sh

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DATE}.sql.gz"

echo "[$(date)] Starting backup process..."

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# 1. Perform Dump
# Using PGPASSWORD environment variable or .pgpass is recommended
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: $BACKUP_FILE"
else
    echo "[$(date)] Backup FAILED!"
    rm -f $BACKUP_FILE
    exit 1
fi

# 2. Rotation (Delete old backups)
echo "[$(date)] Cleaning up backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "[$(date)] Backup process complete."
