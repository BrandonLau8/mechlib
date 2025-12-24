#!/bin/bash
set -e

DB_NAME="mechlib"
DB_USER="mechlib_admin"
DB_CONTAINER="mechlib-postgres"
BACKUP_BUCKET="s3://mechlib-backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/mechlib_backup_${DATE}.sql.gz"

echo "[$(date)] Starting backup..."

# Create backup
if docker exec ${DB_CONTAINER} pg_dump -U ${DB_USER} ${DB_NAME} | gzip > ${BACKUP_FILE}; then
    # Upload to S3
    aws s3 cp ${BACKUP_FILE} ${BACKUP_BUCKET}/daily/ \
        --storage-class STANDARD_IA

    # Send success metric
    aws cloudwatch put-metric-data \
        --namespace MechlibBackups \
        --metric-name BackupSuccess \
        --value 1

    # Cleanup
    rm ${BACKUP_FILE}
    echo "[$(date)] Backup completed"
else
    # Send failure metric
    aws cloudwatch put-metric-data \
        --namespace MechlibBackups \
        --metric-name BackupSuccess \
        --value 0
    echo "[$(date)] Backup failed"
    exit 1
fi

# Add to crontab
# crontab -e

# Add this line (runs daily at 2 AM)
# 0 2 * * * /home/ubuntu/mechlib/backup.sh >> /home/ubuntu/mechlib/backup.log 2>&1