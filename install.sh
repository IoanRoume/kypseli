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
INSTALL_DIR="/usr/local/bin"
# ---------------------

YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE="linux";;
    Darwin*)    OS_TYPE="macos";;
    *)          echo "Unsupported OS: ${OS}"; exit 1;;
esac

DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}-${OS_TYPE}"

echo "🐝 Initializing Kypseli Hive installation..."

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

echo "Downloading Kypseli for ${OS_TYPE}..."
curl -fsSL "$DOWNLOAD_URL" -o "/tmp/${BINARY_NAME}"

echo "Installing to ${INSTALL_DIR}..."
$SUDO mv "/tmp/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"
$SUDO chmod +x "${INSTALL_DIR}/${BINARY_NAME}"

SHELL_NAME=$(basename "$SHELL")
PROFILE=""
case "$SHELL_NAME" in
    zsh)  PROFILE="$HOME/.zshrc";;
    bash) PROFILE="$HOME/.bashrc";;
esac

if [ -n "$PROFILE" ] && [ -f "$PROFILE" ]; then
    if ! grep -q "_KYPSELI_COMPLETE" "$PROFILE"; then
        echo "eval \"\$(_KYPSELI_COMPLETE=${SHELL_NAME}_source ${BINARY_NAME})\"" >> "$PROFILE"
    fi
fi

echo "${YELLOW}"
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
echo "${NC}"
echo "------------------------------------------------"
echo "${CYAN}KYPSELI${NC} is successfully installed!"
echo ""
echo "Run: ${CYAN}source $PROFILE${NC}"
echo "Then type: ${CYAN}kypseli --help${NC}"
echo "------------------------------------------------"