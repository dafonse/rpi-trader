#!/bin/bash

# RPI Trader BVM Deployment Script
# This script automates the setup of BVM and Windows 11 for MetaTrader 5 integration

set -e  # Exit on any error

# Colors for output
RED=\'\\033[0;31m\'
GREEN=\'\\033[0;32m\'
YELLOW=\'\\033[1;33m\'
BLUE=\'\\033[0;34m\'
NC=\'\\033[0m\' # No Color

# Configuration
BVM_DIR="/home/pi/bvm"
VM_PATH="/home/pi/mt5-vm"
USER="pi"

# Logging function
log() {
    echo -e "${BLUE}[$(date +\'%Y-%m-%d %H:%M:%S\')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as user \'pi\'."
        exit 1
    fi
}

# Install BVM dependencies
install_bvm_dependencies() {
    log "Installing BVM system dependencies..."
    sudo apt update
    sudo apt install -y qemu-system-arm qemu-utils libvirt-daemon-system libvirt-clients bridge-utils virt-manager
    sudo usermod -a -G libvirt $USER
    success "BVM system dependencies installed"
}

# Clone BVM repository
clone_bvm() {
    log "Cloning BVM repository..."
    if [ -d "$BVM_DIR" ]; then
        log "BVM directory already exists, skipping clone."
    else
        git clone https://github.com/Botspot/bvm $BVM_DIR
        success "BVM repository cloned."
    fi
}

# Create and configure BVM
create_and_configure_bvm() {
    log "Creating and configuring BVM for MT5..."
    cd $BVM_DIR
    
    if [ -d "$VM_PATH" ]; then
        log "VM directory already exists, skipping new-vm creation."
    else
        ./bvm new-vm $VM_PATH
        success "New VM created at $VM_PATH."
    fi

    log "Updating BVM configuration..."
    # Use sed to update bvm-config file
    sed -i "s/^ram_gb=.*/ram_gb=4/" "$VM_PATH/bvm-config"
    sed -i "s/^shared_folder=.*/shared_folder=\"$PROJECT_DIR\/shared\"/" "$VM_PATH/bvm-config"
    sed -i "s/^enable_rdp=.*/enable_rdp=true/" "$VM_PATH/bvm-config"
    sed -i "s/^timezone=.*/timezone=\"America\/Sao_Paulo\"/" "$VM_PATH/bvm-config"
    
    mkdir -p "$PROJECT_DIR/shared"
    success "BVM configured for MT5."
}

# Download and install Windows 11
install_windows_11() {
    log "Downloading and installing Windows 11..."
    cd $BVM_DIR
    
    log "Downloading Windows 11 ARM ISO (this may take a while)..."
    ./bvm download $VM_PATH
    success "Windows 11 ISO downloaded."

    log "Preparing Windows 11 installation..."
    ./bvm prepare $VM_PATH
    success "Windows 11 installation prepared."

    log "Starting first boot for Windows 11 installation (this will take 30-60 minutes, do NOT interrupt)..."
    ./bvm firstboot $VM_PATH
    success "Windows 11 installed in BVM."
}

# Main deployment function
main() {
    log "Starting RPI Trader BVM deployment..."
    
    check_root
    
    install_bvm_dependencies
    clone_bvm
    create_and_configure_bvm
    install_windows_11
    
    log "BVM and Windows 11 setup complete. Proceed to manual steps for MT5 and Bridge Service."
    echo ""
    echo "Next Steps (Manual in Windows VM):"
    echo "1. Start the VM: cd $BVM_DIR && ./bvm boot-nodisplay $VM_PATH"
    echo "2. Connect via RDP: cd $BVM_DIR && ./bvm connect $VM_PATH"
    echo "3. Install MetaTrader 5 in the Windows VM."
    echo "4. Install Python in the Windows VM (python.org, add to PATH)."
    echo "5. Install Python packages in Windows VM: pip install MetaTrader5 flask requests flask-cors"
    echo "6. Copy the MT5_BRIDGE_SERVICE.py file to C:\\mt5_bridge\\ in the Windows VM."
    echo "7. Run the MT5 Bridge Service: python C:\\mt5_bridge\\mt5_bridge_service.py"
    echo "   (Consider setting it up as a Windows service for auto-start)"
    echo "8. Update your RPI Trader .env file with BVM_MT5_ENABLED=true and MT5 credentials."
    echo "9. Restart RPI Trader services: cd $PROJECT_DIR && ./scripts/deploy.sh restart"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "start_vm")
        log "Starting BVM VM..."
        cd $BVM_DIR
        ./bvm boot-nodisplay $VM_PATH
        ;;
    "connect_vm")
        log "Connecting to BVM VM via RDP..."
        cd $BVM_DIR
        ./bvm connect $VM_PATH
        ;;
    "stop_vm")
        log "Stopping BVM VM..."
        cd $BVM_DIR
        ./bvm shutdown $VM_PATH
        ;;
    *)
        echo "Usage: $0 {deploy|start_vm|connect_vm|stop_vm}"
        echo
        echo "Commands:"
        echo "  deploy     - Full BVM and Windows 11 deployment (default)"
        echo "  start_vm   - Start the BVM VM headless"
        echo "  connect_vm - Connect to the BVM VM via RDP"
        echo "  stop_vm    - Shutdown the BVM VM"
        exit 1
        ;;
esac


