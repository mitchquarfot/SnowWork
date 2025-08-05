#!/bin/bash

# Local Development Setup Script for S3 File Uploader

echo "🔧 Setting up S3 File Uploader for local development..."

# Create .env file from template
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp env_template .env
    echo "✅ .env file created. Please edit it with your actual credentials."
else
    echo "ℹ️ .env file already exists."
fi

# Create streamlit secrets directory and file
echo "📄 Setting up Streamlit secrets for local testing..."
mkdir -p ~/.streamlit
if [ ! -f ~/.streamlit/secrets.toml ]; then
    cp secrets.toml ~/.streamlit/secrets.toml
    echo "✅ Streamlit secrets file created at ~/.streamlit/secrets.toml"
else
    echo "ℹ️ Streamlit secrets file already exists."
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "🎉 Setup complete! You can now run the app locally with:"
echo "   streamlit run streamlit_app.py"
echo ""
echo "📋 Next steps:"
echo "   1. Edit .env with your actual AWS credentials"
echo "   2. Run: streamlit run streamlit_app.py"
echo "   3. Test the app before deploying to Snowflake"