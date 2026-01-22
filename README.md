# Mental Health Chat Bot

Short description
- A small chat-bot project (local development) containing `bot.py` and a Python virtual environment at `mental-health-env`.

Prerequisites
- Python 3.10+ on Windows
- (Optional) Use the provided virtual environment `mental-health-env` or create your own.

Quick setup (using the included venv)

Powershell
```powershell
& .\mental-health-env\Scripts\Activate.ps1
pip install -r requirements.txt  # if you have a requirements file
```

Command Prompt (cmd.exe)
```bat
mental-health-env\Scripts\activate.bat
pip install -r requirements.txt
```

If you don't have the venv, create one and install dependencies:
```bash
python -m venv venv
# Windows PowerShell
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the bot
- Run the main script:
```bash
python bot.py
```

- If the project includes a Streamlit UI, run:
```bash
streamlit run bot.py
```

Notes
- The workspace already contains `mental-health-env` with common packages installed. If you plan to reproduce the environment on another machine, generate a `requirements.txt` with `pip freeze > requirements.txt` from the venv and commit it.

Contributing
- Open an issue or submit a pull request with improvements.

Files of interest
- [bot.py](bot.py)
- [mental-health-env](mental-health-env)

If you want, I can (1) generate a `requirements.txt` from the existing venv, (2) add a short usage example for `bot.py`, or (3) update the README with badges or a license. Which would you like next?