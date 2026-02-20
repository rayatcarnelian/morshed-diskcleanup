# Morshed's Deletor Application

A fast, web-based local application for finding and deleting large files safely from your computer.

## Features
- **Fast Scanning**: Rapidly scans your computer for large files (like videos, applications, and archives).
- **Safe by Default**: Protects system files by default, while making it easy to clean up safe temporary files.
- **Smart Filtering**: Group files by category (Media, Images, Documents, Applications, etc.) and sort them by size.
- **Show in Folder**: Click the "Show in Folder" button to open the exact file location in your Windows Explorer so you can review a video or document before deleting it.
- **Force Deletion**: Gives you ultimate control by letting you bypass safety locks with a warning.

## How to Install and Run

### Prerequisites
You will need to have [Python](https://www.python.org/downloads/) installed on your computer.

### Quick Start
1. **Download the project**: Click the green "Code" button and select "Download ZIP". Extract the folder to your computer.
2. **Setup the Environment**:
   Open a terminal (Command Prompt or PowerShell) in the extracted folder and run:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   cd backend
   pip install -r requirements.txt
   cd ..
   ```
3. **Run the Application**:
   Simply double-click the `run_app.bat` file! 
   
   *This will automatically start the server and open your web browser to the application dashboard.*

## Note on Privacy & Security
This application runs **100% locally** on your own computer. Your files and scan results are never uploaded to any cloud server or sent anywhere over the internet.
