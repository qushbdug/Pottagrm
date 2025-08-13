#!/bin/bash

# Yemen Net Bot Setup Script
# This script sets up the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.11"
VENV_NAME="venv"

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

# Check Python version
check_python() {
    log_info "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION_ACTUAL=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        log_info "Found Python $PYTHON_VERSION_ACTUAL"
        
        if [ "$PYTHON_VERSION_ACTUAL" != "$PYTHON_VERSION" ]; then
            log_warning "Python version mismatch. Expected $PYTHON_VERSION, found $PYTHON_VERSION_ACTUAL"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_error "Python3 not found. Please install Python $PYTHON_VERSION or later."
        exit 1
    fi
}

# Check pip
check_pip() {
    log_info "Checking pip..."
    
    if command -v pip3 &> /dev/null; then
        log_success "pip3 found"
    else
        log_error "pip3 not found. Please install pip."
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."
    
    if [ -d "$VENV_NAME" ]; then
        log_warning "Virtual environment already exists"
        read -p "Remove and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_NAME"
        else
            log_info "Using existing virtual environment"
            return
        fi
    fi
    
    python3 -m venv "$VENV_NAME"
    log_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    log_info "Activating virtual environment..."
    source "$VENV_NAME/bin/activate"
    log_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi
}

# Install development dependencies
install_dev_dependencies() {
    log_info "Installing development dependencies..."
    
    pip install pytest black flake8 pre-commit
    log_success "Development dependencies installed"
}

# Setup pre-commit hooks
setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        log_success "Pre-commit hooks installed"
    else
        log_warning "pre-commit not found, skipping hooks setup"
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p data logs tests
    log_success "Directories created"
}

# Setup environment file
setup_env() {
    log_info "Setting up environment file..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warning "Created .env from .env.example. Please edit it with your settings."
        else
            log_warning "No .env.example found. Please create .env manually."
        fi
    else
        log_info ".env file already exists"
    fi
}

# Run initial tests
run_tests() {
    log_info "Running initial tests..."
    
    if command -v pytest &> /dev/null; then
        pytest tests/ -v || log_warning "Some tests failed, but continuing setup"
    else
        log_warning "pytest not found, skipping tests"
    fi
}

# Show next steps
show_next_steps() {
    echo
    log_success "🎉 Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Edit .env file with your bot token and settings"
    echo "2. Activate virtual environment: source $VENV_NAME/bin/activate"
    echo "3. Run the bot: make run"
    echo "4. Run tests: make test"
    echo "5. Check help: make help"
    echo
    echo "Happy coding! 🚀"
}

# Main setup function
main() {
    log_info "🚀 Starting Yemen Net Bot setup..."
    
    check_python
    check_pip
    create_venv
    activate_venv
    install_dependencies
    
    # Ask about development setup
    echo
    read -p "Install development dependencies? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_dev_dependencies
        setup_pre_commit
    fi
    
    create_directories
    setup_env
    run_tests
    show_next_steps
}

# Run main function
main "$@"