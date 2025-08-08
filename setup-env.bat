@echo off
REM ----------------------------------------------------------------------------
REM  This script is GPT4o generated
REM  setup-env.bat
REM  This script checks if a Python virtual environment folder named "env"
REM  exists in the current directory. 
REM    1) If it does not exist, it creates one using python -m venv env.
REM    2) Activates the virtual environment.
REM    3) Installs packages from requirements.txt if found.
REM    4) Upgrades pip to avoid version-related issues.
REM ----------------------------------------------------------------------------

echo Checking for Python virtual environment...

IF NOT EXIST ".env\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one...
    python -m venv .env
) else (
    echo Virtual environment already exists.
)

echo Activating environment...
call env\Scripts\activate.bat

REM Use the environment's Python executable
SET VENV_PYTHON=.env\Scripts\python.exe

echo Upgrading pip to the latest version...
%VENV_PYTHON% -m pip install --upgrade pip

echo Checking for requirements.txt...
IF EXIST requirements.txt (
    echo Installing packages from requirements.txt...
    %VENV_PYTHON% -m pip install -r requirements.txt
) else (
    echo No requirements.txt file found. Skipping package installation.
)

echo Python virtual environment is now active.

echo setup complete