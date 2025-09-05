#!/bin/bash
# Setup script for llama.cpp generation server on macOS M1

set -e

echo "🚀 Setting up llama.cpp generation server..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Install llama.cpp
echo "📦 Installing llama.cpp..."
if ! command -v llama-server &> /dev/null; then
    brew install llama.cpp
else
    echo "✅ llama.cpp already installed"
fi

# Create models directory
MODELS_DIR="/Users/$(whoami)/models"
mkdir -p "$MODELS_DIR"
echo "📁 Models directory: $MODELS_DIR"

# Function to download model if not exists
download_model() {
    local model_name="$1"
    local model_url="$2"
    local model_path="$MODELS_DIR/$model_name"
    
    if [ ! -f "$model_path" ]; then
        echo "📥 Downloading $model_name..."
        echo "   This may take several minutes..."
        curl -L -o "$model_path" "$model_url"
        echo "✅ Downloaded: $model_path"
    else
        echo "✅ Model already exists: $model_path"
    fi
}

# Download Qwen 1.7B model (lightweight for testing)
echo "🔄 Setting up Qwen 1.7B Instruct model..."
download_model "Qwen2-1.5B-Instruct-Q4_K_M.gguf" \
    "https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf"

# Create startup scripts
cat > "$MODELS_DIR/start_qwen.sh" << 'EOF'
#!/bin/bash
# Start Qwen 1.5B Instruct server (lightweight)
MODELS_DIR="/Users/$(whoami)/models"

echo "🚀 Starting Qwen 1.5B Instruct server on port 8004..."
echo "📍 Model: Qwen2-1.5B-Instruct (Q4_K_M)"
echo "📍 Context: 8192 tokens"
echo "📍 Metal GPU acceleration enabled"
echo "📍 OpenAI-compatible API on http://localhost:8004"

llama-server \
  -m "$MODELS_DIR/Qwen2-1.5B-Instruct-Q4_K_M.gguf" \
  -c 8192 \
  -ngl 999 \
  -t 8 \
  --port 8004 \
  --host 0.0.0.0 \
  --chat-template qwen \
  --log-format text
EOF

chmod +x "$MODELS_DIR/start_qwen.sh"

# Create test script
cat > "$MODELS_DIR/test_generation.sh" << 'EOF'
#!/bin/bash
# Test the generation server

echo "🧪 Testing generation server..."

curl -s http://localhost:8004/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2-1.5b-instruct",
    "messages": [{"role": "user", "content": "Give me one calming evening tip in 20 words or less."}],
    "max_tokens": 50,
    "temperature": 0.7
  }' | jq -r '.choices[0].message.content'
EOF

chmod +x "$MODELS_DIR/test_generation.sh"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start the generation server:"
echo "   $MODELS_DIR/start_qwen.sh"
echo ""
echo "2. Test the server (in another terminal):"
echo "   $MODELS_DIR/test_generation.sh"
echo ""
echo "3. Health check:"
echo "   curl http://localhost:8004/health"
echo ""
echo "📁 All files created in: $MODELS_DIR"