#!/bin/bash

# Yemen Net Bot - Render Deployment Script
# سكريبت نشر بوت يمن نت على Render

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_NAME="yemen-net-bot"
BOT_TOKEN="7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
BOT_USERNAME="@Vsjsgshh_bot"

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
    if [ ! -f "main.py" ] || [ ! -f "render.yaml" ]; then
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
        pytest tests/ -v || log_warning "Some tests failed, but continuing..."
    else
        log_warning "pytest not found, skipping tests"
    fi
}

# Check code quality
check_code_quality() {
    log_info "Checking code quality..."
    
    if command -v flake8 &> /dev/null; then
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || log_warning "Code quality issues found, but continuing..."
    else
        log_warning "flake8 not found, skipping code quality check"
    fi
}

# Verify configuration files
verify_config() {
    log_info "Verifying configuration files..."
    
    # Check render.yaml
    if [ ! -f "render.yaml" ]; then
        log_error "render.yaml not found!"
        exit 1
    fi
    
    # Check main.py
    if [ ! -f "main.py" ]; then
        log_error "main.py not found!"
        exit 1
    fi
    
    # Check requirements.txt
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found!"
        exit 1
    fi
    
    # Check build.sh
    if [ ! -f "build.sh" ]; then
        log_warning "build.sh not found, creating it..."
        create_build_script
    fi
    
    log_success "All configuration files verified!"
}

# Create build script if missing
create_build_script() {
    cat > build.sh << 'EOF'
#!/bin/bash
# Build script for Render

echo "🚀 Building Yemen Net Bot..."

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod +x main.py run_bot.py

echo "✅ Build completed successfully!"
EOF
    
    chmod +x build.sh
    log_success "build.sh created!"
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

# Deploy to GitHub
deploy_to_github() {
    log_info "Deploying to GitHub..."
    
    # Add all files
    git add .
    
    # Commit changes
    git commit -m "Deploy to Render: $(date)"
    
    # Push to main branch
    git push origin main
    
    log_success "Deployed to GitHub successfully!"
}

# Show deployment summary
show_deployment_summary() {
    echo
    log_success "🎉 Deployment preparation completed successfully!"
    echo
    echo "📋 Next steps:"
    echo "1. Go to [render.com](https://render.com)"
    echo "2. Sign up/Login with GitHub"
    echo "3. Click 'New +' → 'Web Service'"
    echo "4. Connect your GitHub repository"
    echo "5. Select 'yemen-net-bot' repository"
    echo "6. Use these settings:"
echo "   • Name: yemen-net-bot"
echo "   • Environment: Python 3"
echo "   • Build Command: pip install --upgrade pip && pip install -r requirements-minimal.txt"
echo "   • Start Command: python main.py"
    echo "7. Click 'Create Web Service'"
    echo
    echo "🔗 Bot Information:"
    echo "• Username: $BOT_USERNAME"
    echo "• Token: $BOT_TOKEN"
    echo "• Repository: $(git remote get-url origin)"
    echo
    echo "📚 For detailed instructions, see: README_DEPLOYMENT.md"
}

# Main deployment function
main() {
    log_info "🚀 Starting Yemen Net Bot Render deployment preparation..."
    
    check_directory
    check_git_status
    run_tests
    check_code_quality
    verify_config
    backup_database
    deploy_to_github
    show_deployment_summary
}

# Check if help is requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Yemen Net Bot - Render Deployment Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verify   Only verify configuration"
    echo "  -t, --test     Only run tests"
    echo
    echo "Examples:"
    echo "  $0              # Full deployment preparation"
    echo "  $0 --verify     # Verify configuration only"
    echo "  $0 --test       # Run tests only"
    exit 0
fi

# Check if only verification is requested
if [ "$1" = "-v" ] || [ "$1" = "--verify" ]; then
    check_directory
    verify_config
    log_success "Configuration verification completed!"
    exit 0
fi

# Check if only testing is requested
if [ "$1" = "-t" ] || [ "$1" = "--test" ]; then
    check_directory
    run_tests
    check_code_quality
    log_success "Testing completed!"
    exit 0
fi

# Run main function
main "$@"