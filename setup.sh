#!/bin/bash
# Chess Roguelike - One-Time Setup Script (macOS / Linux)

set -e

echo ""
echo "=== Chess Roguelike Setup ==="
echo ""

# --- macOS: install Homebrew if needed ---
if [[ "$(uname)" == "Darwin" ]]; then
    if ! command -v brew &>/dev/null; then
        echo "Installing Homebrew (you may be prompted for your password)..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for Apple Silicon Macs
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "Homebrew already installed."
    fi
fi

# --- Install Python 3 ---
if ! command -v python3 &>/dev/null; then
    echo "Installing Python 3..."
    if [[ "$(uname)" == "Darwin" ]]; then
        brew install python@3
    else
        # Linux (Debian/Ubuntu)
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
    fi
else
    echo "Python 3 already installed."
fi

# --- Install Git ---
if ! command -v git &>/dev/null; then
    echo "Installing Git..."
    if [[ "$(uname)" == "Darwin" ]]; then
        brew install git
    else
        sudo apt-get update && sudo apt-get install -y git
    fi
else
    echo "Git already installed."
fi

# --- Clone or update the game ---
GAME_DIR="$HOME/Games/ChessRoguelike"
echo "Downloading game to $GAME_DIR..."

if [[ -d "$GAME_DIR/.git" ]]; then
    echo "Game already downloaded. Updating..."
    cd "$GAME_DIR"
    git pull
else
    mkdir -p "$GAME_DIR"
    git clone https://github.com/marrichard/Chess.git "$GAME_DIR"
    cd "$GAME_DIR"
fi

# --- Install Python dependencies ---
echo "Installing game dependencies..."
python3 -m pip install -r requirements.txt --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install -r requirements.txt --quiet

# --- Create desktop launchers ---
DESKTOP="$HOME/Desktop"

# Play launcher
cat > "$DESKTOP/Play Chess Roguelike.command" << 'LAUNCHER'
#!/bin/bash
cd "$HOME/Games/ChessRoguelike"
python3 main.py
LAUNCHER
chmod +x "$DESKTOP/Play Chess Roguelike.command"

# Update launcher
cat > "$DESKTOP/Update Chess Roguelike.command" << 'UPDATER'
#!/bin/bash
echo "Updating Chess Roguelike..."
cd "$HOME/Games/ChessRoguelike"
git pull
python3 -m pip install -r requirements.txt --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install -r requirements.txt --quiet
echo ""
echo "Updated! You can close this window and click Play."
read -p "Press Enter to close..."
UPDATER
chmod +x "$DESKTOP/Update Chess Roguelike.command"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Two files are on your desktop:"
echo "  Play Chess Roguelike.command    - Double-click to play"
echo "  Update Chess Roguelike.command  - Double-click when told to update"
echo ""
read -p "Press Enter to close..."
