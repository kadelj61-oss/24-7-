#!/bin/bash

# Setup script for GitHub repository

echo "=== Camera Streaming Server - GitHub Setup ==="
echo ""

# Get user info
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter repository name (default: camera-streaming-server): " REPO_NAME
REPO_NAME=${REPO_NAME:-camera-streaming-server}

echo ""
echo "Creating project structure..."

# Create directories
mkdir -p config src static docker systemd nginx logs recordings tests .github/workflows .github/ISSUE_TEMPLATE

# Create .gitkeep files
touch logs/.gitkeep recordings/.gitkeep

echo "Initializing git repository..."
git init

echo "Adding all files..."
git add .

echo "Creating initial commit..."
git commit -m "Initial commit: 24/7 camera streaming server with multiprocessing"

echo ""
echo "Next steps:"
echo "1. Go to https://github.com/new"
echo "2. Create a repository named: $REPO_NAME"
echo "3. Don't initialize with README"
echo "4. Run these commands:"
echo ""
echo "   git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "Setup complete!"
chmod +x setup_project.sh
./setup_project.sh
