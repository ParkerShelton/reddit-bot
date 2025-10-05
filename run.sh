#!/bin/bash

# Script to run the Reddit bot console interface with dependency checks
echo "Starting Reddit Bot Setup..."

# Determine Python command to use
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Check if python is Python 3
    PY_VERSION=$(python --version 2>&1 | grep -oP '(?<=Python )\d')
    if [ "$PY_VERSION" == "3" ]; then
        PYTHON_CMD="python"
    else
        echo "Error: Python 3 is required but not found."
        echo "Please install Python 3 or make sure it's in your PATH."
        exit 1
    fi
else
    echo "Error: Python 3 is required but not found."
    echo "Please install Python 3 or make sure it's in your PATH."
    exit 1
fi

# Check if the install.py file exists
if [ -f "install.py" ]; then
    echo "Checking required dependencies..."
    $PYTHON_CMD install.py
    
    # Check if installation succeeded
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install required dependencies. Please check the error messages above."
        exit 1
    fi
    
    echo -e "\nStarting Reddit Bot Console Interface...\n"
else
    echo "Warning: install.py not found. Skipping dependency check."
fi

# Run the console interface
$PYTHON_CMD console_interface.py

# Exit with the same status as the Python script
exit $?
