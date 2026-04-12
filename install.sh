#!/usr/bin/env bash
set -euo pipefail

echo "Installing narrate..."

# Check for uv, install if missing
if ! command -v uv &>/dev/null; then
    echo "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the env so uv is available in this session
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install narrate as a uv tool
uv tool install git+https://github.com/zackham/narrate.git

echo ""
echo "narrate installed successfully!"
echo ""
echo "Quick start:"
echo "  narrate install-voices"
echo "  narrate --text 'Hello world' --voice adrian -o hello.mp3"
