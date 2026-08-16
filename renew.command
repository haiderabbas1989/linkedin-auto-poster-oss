#!/bin/bash
# Double-click this file to renew your LinkedIn token.
# (On first use, macOS may ask you to allow it in System Settings > Privacy & Security.)
cd "$(dirname "$0")"
python3 setup.py
echo ""
echo "Press any key to close this window..."
read -n 1
