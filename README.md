[README_SETUP.txt](https://github.com/user-attachments/files/26060077/README_SETUP.txt)
VASRD Toolkit - Setup (Windows)
=================================

1) Install Python from python.org (NOT the Microsoft Store)
   - https://www.python.org/downloads/windows/
   - During install, CHECK: "Add Python to PATH" and "Install pip"
   - Verify in a new CMD:  python --version

2) Create a project folder and place these files together:
   - main.py
   - vasrd_gui.py
   - vasrd_scraper.py
   - vasrd_schema.py
   - requirements.txt  (runtime)
   - requirements-dev.txt (build)
   - installer.nsi (optional, for NSIS installer)

3) Create a virtual environment (recommended)
   python -m venv .venv
   .venv\Scriptsctivate

4) Install dependencies
   python -m pip install --upgrade pip
   pip install -r requirements.txt

5) Run the app
   python main.py

6) Build a one-file EXE (PyInstaller 6.19+)
   pip install -r requirements-dev.txt
   python -m PyInstaller --clean --onefile --windowed main.py
   # Output will be in dist\main.exe (rename to VASRD_Toolkit.exe if desired)

7) Optional: Build a Windows installer (NSIS)
   - Install NSIS: https://nsis.sourceforge.io/Download
   - Ensure dist\VASRD_Toolkit.exe exists (rename dist\main.exe accordingly)
   - Compile: "C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
   - Result: VASRD_Toolkit_Setup.exe (distributable installer)

Troubleshooting
---------------
- If you see "No module named PyInstaller" or "pyinstaller not recognized":
  * Ensure you are using the python.org installation.
  * Re-open a NEW terminal after PATH changes.
  * Install dev deps: pip install -r requirements-dev.txt

- If import fails with XML errors: eCFR may be rate-limiting; try again later.

- If search returns no results after import: confirm that the eCFR date is valid (YYYY-MM-DD) and re-run Import.
