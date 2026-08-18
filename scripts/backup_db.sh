#!/bin/bash
# CommerceOS Database Backup Script
# Usage: ./scripts/backup_db.sh
# Creates a timestamped backup of the CommerceOS database.

set -euo pipefail

DB_PATH="${DB_PATH:-commerceos.db}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/commerceos_${TIMESTAMP}.db"

mkdir -p "${BACKUP_DIR}"

if [ ! -f "${DB_PATH}" ]; then
    echo "ERROR: Database file not found at ${DB_PATH}"
    exit 1
fi

cp "${DB_PATH}" "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"
echo "Size: $(du -h "${BACKUP_FILE}" | cut -f1)"

# Optional: keep only the last N backups
KEEP_N="${KEEP_N:-10}"
ls -t "${BACKUP_DIR}"/commerceos_*.db | tail -n +$((KEEP_N + 1)) | xargs -r rm
echo "Kept last ${KEEP_N} backups."
