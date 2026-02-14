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
REPO="IoanRoume/kypseli"
BINARY_NAME="kypseli"
INSTALL_DIR="/usr/local/kypseli"
BIN_LINK="/usr/local/bin/kypseli"
VERSION="0.7.5"
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

print_error() {
    printf "  ${RED}[✗]${NC} %s\n" "$1"
}

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE="linux";;
    Darwin*)    OS_TYPE="macos";;
    *)          printf "${RED}Unsupported OS: ${OS}${NC}\n"; exit 1;;
esac

DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}-${OS_TYPE}.tar.gz"

# Header
printf "\n"
printf "${YELLOW}  ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡${NC}\n"
printf "${YELLOW}  ⬡                           ⬡${NC}\n"
printf "${YELLOW}  ⬡${NC}   🐝 ${CYAN}KYPSELI INSTALLER${NC}   ${YELLOW}⬡${NC}\n"
printf "${YELLOW}  ⬡${NC}      ${DIM}v${VERSION}${NC}             ${YELLOW}⬡${NC}\n"
printf "${YELLOW}  ⬡                           ⬡${NC}\n"
printf "${YELLOW}  ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡${NC}\n"
printf "\n"
printf "  Installing for ${CYAN}${OS_TYPE}${NC}...\n"
printf "\n"

# Check for required tools
if ! command -v curl >/dev/null 2>&1; then
    print_error "curl is required but not installed"
    exit 1
fi
print_step "Found curl"

if ! command -v tar >/dev/null 2>&1; then
    print_error "tar is required but not installed"
    exit 1
fi
print_step "Found tar"

# Check for sudo
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
        print_step "Found sudo"
    else
        print_error "This script requires root privileges"
        exit 1
    fi
fi

printf "\n"

# Download with curl's built-in progress bar
printf "  ${YELLOW}[↓]${NC} Downloading from GitHub...\n"
printf "\n"
if curl -fL "$DOWNLOAD_URL" -o "/tmp/${BINARY_NAME}.tar.gz" --progress-bar 2>&1; then
    printf "  ${GREEN}[✓]${NC} Download complete\n"
else
    printf "  ${RED}[✗]${NC} Failed to download\n"
    printf "  ${DIM}URL: ${DOWNLOAD_URL}${NC}\n"
    exit 1
fi

printf "\n"

# Extract
printf "  ${YELLOW}[...]${NC} Extracting archive...\r"
cd /tmp
if tar -xzf "${BINARY_NAME}.tar.gz" 2>/dev/null; then
    rm "${BINARY_NAME}.tar.gz"
    printf "  ${GREEN}[✓]${NC} Extracted archive    \n"
else
    printf "  ${RED}[✗]${NC} Failed to extract    \n"
    exit 1
fi

# Install
printf "  ${YELLOW}[...]${NC} Installing...\r"
$SUDO rm -rf "${INSTALL_DIR}" 2>/dev/null || true
$SUDO mkdir -p "${INSTALL_DIR}"
$SUDO mv /tmp/${BINARY_NAME}/* "${INSTALL_DIR}/"
$SUDO chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
rm -rf "/tmp/${BINARY_NAME}" 2>/dev/null || true
$SUDO ln -sf "${INSTALL_DIR}/${BINARY_NAME}" "${BIN_LINK}"
printf "  ${GREEN}[✓]${NC} Installed to ${INSTALL_DIR}\n"

# Setup shell completion
SHELL_NAME=$(basename "$SHELL")
PROFILE=""
case "$SHELL_NAME" in
    zsh)  PROFILE="$HOME/.zshrc";;
    bash) PROFILE="$HOME/.bashrc";;
esac

if [ -n "$PROFILE" ] && [ -f "$PROFILE" ]; then
    if ! grep -q "_KYPSELI_COMPLETE" "$PROFILE" 2>/dev/null; then
        echo "eval \"\$(_KYPSELI_COMPLETE=${SHELL_NAME}_source ${BINARY_NAME})\"" >> "$PROFILE"
        print_step "Added shell completion to ${PROFILE}"
    else
        print_step "Shell completion already configured"
    fi
fi

# Success!
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
printf "  ${GREEN}║${NC}  ${CYAN}KYPSELI${NC} installed successfully!     ${GREEN}║${NC}\n"
printf "  ${GREEN}════════════════════════════════════════${NC}\n"
printf "\n"
printf "  ${DIM}Version:${NC}   ${VERSION}\n"
printf "  ${DIM}Location:${NC}  ${INSTALL_DIR}\n"
printf "  ${DIM}Binary:${NC}    ${BIN_LINK}\n"
printf "\n"

if [ -n "$PROFILE" ]; then
    printf "  ${YELLOW}Next steps:${NC}\n"
    printf "    1. Run: ${CYAN}source ${PROFILE}${NC}\n"
    printf "    2. Then: ${CYAN}kypseli --help${NC}\n"
else
    printf "  ${YELLOW}Next step:${NC}\n"
    printf "    Run: ${CYAN}kypseli --help${NC}\n"
fi

printf "\n"
printf "  ${DIM}Documentation: https://github.com/${REPO}${NC}\n"
printf "\n"