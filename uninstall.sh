#!/bin/sh
# Copyright 2026 Ioannis Roumeliotis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
set -e

# --- CONFIGURATION ---
BINARY_NAME="kypseli"
INSTALL_DIR="/usr/local/kypseli"
BIN_LINK="/usr/local/bin/kypseli"
DATA_DIR="$HOME/.file_organizer"
# ---------------------

YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GREEN='\033[0;32m'
DIM='\033[2m'
NC='\033[0m'

print_step() {
    printf "  ${GREEN}[✓]${NC} %s\n" "$1"
}

print_skip() {
    printf "  ${DIM}[~]${NC} %s\n" "$1"
}

print_error() {
    printf "  ${RED}[✗]${NC} %s\n" "$1"
}

# Header
printf "\n"
printf "${RED}  ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡${NC}\n"
printf "${RED}  ⬡                           ⬡${NC}\n"
printf "${RED}  ⬡${NC}   🐝 ${CYAN}KYPSELI UNINSTALLER${NC} ${RED}⬡${NC}\n"
printf "${RED}  ⬡                           ⬡${NC}\n"
printf "${RED}  ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡${NC}\n"
printf "\n"

# Check if kypseli is installed
if [ ! -d "$INSTALL_DIR" ] && [ ! -L "$BIN_LINK" ] && [ ! -f "$BIN_LINK" ]; then
    printf "  ${YELLOW}Kypseli does not appear to be installed.${NC}\n"
    printf "\n"
    exit 0
fi

# Check for sudo
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        print_error "This script requires root privileges"
        exit 1
    fi
fi

# Confirm uninstall
printf "  This will remove:\n"
printf "    ${CYAN}•${NC} Installation directory: ${INSTALL_DIR}\n"
printf "    ${CYAN}•${NC} Symlink: ${BIN_LINK}\n"
printf "    ${CYAN}•${NC} Shell completion from your profile\n"
printf "\n"
printf "  ${YELLOW}Note:${NC} User data at ${DATA_DIR} will ${GREEN}NOT${NC} be removed.\n"
printf "        Use ${CYAN}--purge${NC} flag to remove user data as well.\n"
printf "\n"

# Check for --purge flag
PURGE=0
for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=1 ;;
        --yes|-y) AUTO_YES=1 ;;
    esac
done

if [ "$PURGE" -eq 1 ]; then
    printf "  ${RED}WARNING:${NC} --purge flag detected. User data WILL be removed!\n"
    printf "\n"
fi

# Ask for confirmation (unless --yes flag)
if [ "$AUTO_YES" != "1" ]; then
    printf "  Continue with uninstall? [y/N] "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) ;;
        *) 
            printf "\n  ${YELLOW}Uninstall cancelled.${NC}\n\n"
            exit 0
            ;;
    esac
fi

printf "\n"

# Stop service if running
if [ -f "$DATA_DIR/service/watcher.pid" ]; then
    printf "  ${YELLOW}[...]${NC} Stopping service...\r"
    PID=$(cat "$DATA_DIR/service/watcher.pid" 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        sleep 1
        print_step "Stopped running service"
    else
        print_skip "Service not running"
    fi
fi

# Remove symlink
if [ -L "$BIN_LINK" ] || [ -f "$BIN_LINK" ]; then
    printf "  ${YELLOW}[...]${NC} Removing symlink...\r"
    $SUDO rm -f "$BIN_LINK"
    print_step "Removed symlink: ${BIN_LINK}"
else
    print_skip "Symlink not found: ${BIN_LINK}"
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    printf "  ${YELLOW}[...]${NC} Removing installation...\r"
    $SUDO rm -rf "$INSTALL_DIR"
    print_step "Removed installation: ${INSTALL_DIR}"
else
    print_skip "Installation not found: ${INSTALL_DIR}"
fi

# Remove shell completion
SHELL_NAME=$(basename "$SHELL")
PROFILE=""
case "$SHELL_NAME" in
    zsh)  PROFILE="$HOME/.zshrc";;
    bash) PROFILE="$HOME/.bashrc";;
esac

if [ -n "$PROFILE" ] && [ -f "$PROFILE" ]; then
    if grep -q "_KYPSELI_COMPLETE" "$PROFILE" 2>/dev/null; then
        printf "  ${YELLOW}[...]${NC} Removing shell completion...\r"
        # Create temp file without the kypseli line
        grep -v "_KYPSELI_COMPLETE" "$PROFILE" > "${PROFILE}.tmp"
        mv "${PROFILE}.tmp" "$PROFILE"
        print_step "Removed shell completion from ${PROFILE}"
    else
        print_skip "Shell completion not found in ${PROFILE}"
    fi
fi

# Remove user data if --purge
if [ "$PURGE" -eq 1 ]; then
    if [ -d "$DATA_DIR" ]; then
        printf "  ${YELLOW}[...]${NC} Removing user data...\r"
        rm -rf "$DATA_DIR"
        print_step "Removed user data: ${DATA_DIR}"
    else
        print_skip "User data not found: ${DATA_DIR}"
    fi
fi

# Success
printf "\n"
printf "${YELLOW}"
cat << "EOF"
              \     /
          \    o ^ o    /
            \ (     ) /
 ____________(%%%%%%%)____________
(     /   /  )%%%%%%%(  \   \     )
(___/___/__/           \__\___\___)
   (     /  /(%%%%%%%)\  \     )
    (__/___/ (%%%%%%%) \___\__)
            /(       )\
          /   (%%%%%)   \
               (%%%)
                 !
EOF
printf "${NC}"
printf "  ${GREEN}════════════════════════════════════════${NC}\n"
printf "  ${GREEN}║${NC}  ${CYAN}KYPSELI${NC} uninstalled successfully!   ${GREEN}║${NC}\n"
printf "  ${GREEN}════════════════════════════════════════${NC}\n"
printf "\n"

if [ "$PURGE" -eq 0 ] && [ -d "$DATA_DIR" ]; then
    printf "  ${DIM}User data preserved at:${NC} ${DATA_DIR}\n"
    printf "  ${DIM}To remove it, run:${NC} rm -rf ${DATA_DIR}\n"
    printf "\n"
fi

if [ -n "$PROFILE" ]; then
    printf "  ${YELLOW}Note:${NC} Run ${CYAN}source ${PROFILE}${NC} to refresh your shell.\n"
    printf "\n"
fi

printf "  ${DIM}Thank you for trying Kypseli! 🐝${NC}\n"
printf "\n"