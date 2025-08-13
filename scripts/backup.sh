#!/bin/bash

# Yemen Net Bot Backup Script
# This script creates backups of the database and important files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups"
DB_FILE="yemen_net.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
create_backup_dir() {
    log_info "Creating backup directory..."
    mkdir -p "$BACKUP_DIR"
    log_success "Backup directory created: $BACKUP_DIR"
}

# Backup database
backup_database() {
    log_info "Backing up database..."
    
    if [ -f "$DB_FILE" ]; then
        BACKUP_NAME="${BACKUP_DIR}/db_backup_${TIMESTAMP}.db"
        cp "$DB_FILE" "$BACKUP_NAME"
        
        # Get file size
        FILE_SIZE=$(du -h "$BACKUP_NAME" | cut -f1)
        log_success "Database backed up: $BACKUP_NAME ($FILE_SIZE)"
        
        # Create checksum
        sha256sum "$BACKUP_NAME" > "${BACKUP_NAME}.sha256"
        log_info "Checksum created: ${BACKUP_NAME}.sha256"
    else
        log_warning "Database file not found: $DB_FILE"
    fi
}

# Backup configuration files
backup_config() {
    log_info "Backing up configuration files..."
    
    CONFIG_FILES=(".env" "render.yaml" "requirements.txt")
    
    for file in "${CONFIG_FILES[@]}"; do
        if [ -f "$file" ]; then
            BACKUP_NAME="${BACKUP_DIR}/config_${file}_${TIMESTAMP}"
            cp "$file" "$BACKUP_NAME"
            log_success "Config backed up: $BACKUP_NAME"
        else
            log_warning "Config file not found: $file"
        fi
    done
}

# Backup logs
backup_logs() {
    log_info "Backing up logs..."
    
    if [ -d "logs" ] && [ "$(ls -A logs)" ]; then
        BACKUP_NAME="${BACKUP_DIR}/logs_backup_${TIMESTAMP}.tar.gz"
        tar -czf "$BACKUP_NAME" logs/
        
        # Get file size
        FILE_SIZE=$(du -h "$BACKUP_NAME" | cut -f1)
        log_success "Logs backed up: $BACKUP_NAME ($FILE_SIZE)"
    else
        log_warning "No logs directory or logs found"
    fi
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups..."
    
    # Keep backups from last 7 days
    find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.sha256" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Old backups cleaned up"
}

# Show backup summary
show_summary() {
    log_info "Backup summary:"
    echo
    
    if [ -d "$BACKUP_DIR" ]; then
        echo "Backup directory: $BACKUP_DIR"
        echo "Total backups: $(ls -1 "$BACKUP_DIR" | wc -l)"
        echo "Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
        echo
        
        echo "Recent backups:"
        ls -la "$BACKUP_DIR" | head -10
    else
        log_warning "No backup directory found"
    fi
}

# Verify backup integrity
verify_backup() {
    log_info "Verifying backup integrity..."
    
    # Check database backup
    DB_BACKUP=$(find "$BACKUP_DIR" -name "db_backup_${TIMESTAMP}.db" | head -1)
    if [ -n "$DB_BACKUP" ]; then
        # Verify checksum
        if [ -f "${DB_BACKUP}.sha256" ]; then
            if cd "$BACKUP_DIR" && sha256sum -c "$(basename "${DB_BACKUP}.sha256")" 2>/dev/null; then
                log_success "Database backup verified successfully"
            else
                log_error "Database backup verification failed!"
            fi
        else
            log_warning "No checksum file found for verification"
        fi
    fi
}

# Main backup function
main() {
    log_info "💾 Starting Yemen Net Bot backup..."
    
    create_backup_dir
    backup_database
    backup_config
    backup_logs
    cleanup_old_backups
    verify_backup
    show_summary
    
    log_success "🎉 Backup completed successfully!"
}

# Check if help is requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Yemen Net Bot Backup Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verify   Only verify existing backups"
    echo "  -s, --summary  Only show backup summary"
    echo
    echo "Examples:"
    echo "  $0              # Create full backup"
    echo "  $0 --verify     # Verify existing backups"
    echo "  $0 --summary    # Show backup summary"
    exit 0
fi

# Check if only verification is requested
if [ "$1" = "-v" ] || [ "$1" = "--verify" ]; then
    verify_backup
    exit 0
fi

# Check if only summary is requested
if [ "$1" = "-s" ] || [ "$1" = "--summary" ]; then
    show_summary
    exit 0
fi

# Run main function
main "$@"