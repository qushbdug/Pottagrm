#!/bin/bash

# Yemen Net Bot Deployment Script
# This script automates the deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_NAME="yemen-net-bot"
DEPLOY_BRANCH="main"
PRODUCTION_BRANCH="production"

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

# Check if we're in the right directory
check_directory() {
    if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi
}

# Check git status
check_git_status() {
    log_info "Checking git status..."
    
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "You have uncommitted changes. Please commit or stash them first."
        git status --short
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Run tests
run_tests() {
    log_info "Running tests..."
    if command -v pytest &> /dev/null; then
        pytest tests/ -v
        if [ $? -eq 0 ]; then
            log_success "All tests passed!"
        else
            log_error "Tests failed! Aborting deployment."
            exit 1
        fi
    else
        log_warning "pytest not found, skipping tests"
    fi
}

# Check code quality
check_code_quality() {
    log_info "Checking code quality..."
    
    if command -v flake8 &> /dev/null; then
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        if [ $? -eq 0 ]; then
            log_success "Code quality check passed!"
        else
            log_warning "Code quality issues found, but continuing..."
        fi
    else
        log_warning "flake8 not found, skipping code quality check"
    fi
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    if [ -f "yemen_net.db" ]; then
        BACKUP_NAME="yemen_net_backup_$(date +%Y%m%d_%H%M%S).db"
        cp yemen_net.db "$BACKUP_NAME"
        log_success "Database backed up as $BACKUP_NAME"
    else
        log_warning "No database file found to backup"
    fi
}

# Deploy to production
deploy_production() {
    log_info "Deploying to production..."
    
    # Switch to production branch
    git checkout $PRODUCTION_BRANCH 2>/dev/null || git checkout -b $PRODUCTION_BRANCH
    
    # Merge main branch
    git merge $DEPLOY_BRANCH --no-edit
    
    # Push to production
    git push origin $PRODUCTION_BRANCH
    
    log_success "Deployed to production branch!"
    
    # Switch back to main
    git checkout $DEPLOY_BRANCH
}

# Deploy to Render
deploy_render() {
    log_info "Deploying to Render..."
    
    # Check if render.yaml exists
    if [ -f "render.yaml" ]; then
        log_info "render.yaml found, Render will auto-deploy"
    else
        log_warning "render.yaml not found, manual deployment required"
    fi
    
    # Push to trigger Render deployment
    git push origin $DEPLOY_BRANCH
    log_success "Pushed to main branch, Render deployment triggered!"
}

# Main deployment function
main() {
    log_info "🚀 Starting Yemen Net Bot deployment..."
    
    check_directory
    check_git_status
    run_tests
    check_code_quality
    backup_database
    
    # Ask user for deployment type
    echo
    echo "Choose deployment type:"
    echo "1) Deploy to production branch"
    echo "2) Deploy to Render (main branch)"
    echo "3) Both"
    echo "4) Cancel"
    
    read -p "Enter your choice (1-4): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            deploy_production
            ;;
        2)
            deploy_render
            ;;
        3)
            deploy_production
            deploy_render
            ;;
        4)
            log_info "Deployment cancelled"
            exit 0
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    log_success "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"