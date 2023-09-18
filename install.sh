#!/bin/bash

# Check if the system has Python 3.x installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3.x is not installed. Please install Python 3.x before proceeding."
    exit 1
fi

# Ask the user for the installation location
echo "In which directory would you like to install the script?"
read -p "Enter the directory (type '.' for the current directory): " install_dir

# Create the installation directory if it does not exist
if [ "$install_dir" != "." ] && [ ! -d "$install_dir" ]; then
    echo "Creating installation directory..."
    mkdir -p "$install_dir"
fi

# Check the Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d'.' -f1)
if [ "$python_version" != "3" ]; then
    echo "The Python version on the system is not 3.x."
    exit 1
fi

# Copy the Python script to the installation directory
cp *.py "$install_dir"

# Check if the pip module is installed
if ! command -v pip3 &> /dev/null; then
    echo "The pip3 module is not installed. Please install it before proceeding."
    exit 1
fi

# Specify the required Python modules
required_modules=("requests" "python-telegram-bot" "m3u8")

# Install the required Python modules
echo "Installing the required Python modules..."
for module in "${required_modules[@]}"; do
    pip3 install "$module"
done

# Check if the installation was successful
if [ $? -eq 0 ]; then
    echo "Installation completed successfully."
else
    echo "Error during the installation of Python modules."
    exit 1
fi

exit 0