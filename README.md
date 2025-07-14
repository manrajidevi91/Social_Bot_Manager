# Flask Bot Manager

This repository contains a small Flask application that helps manage other Flask based bots. It relies on a few environment variables and has helper scripts to set up a Python virtual environment and start the server.

## Setting the Base Directory

The app looks for an environment variable named `BOT_MANAGER_HOME` to locate all of its data folders. If not provided, it falls back to the directory containing this repository. You can export it for the current session or add it to your `~/.bashrc`:

```bash
export BOT_MANAGER_HOME=/opt/bot_manager
```

Create the directory if it does not already exist and copy the project files there. All uploaded bots and the virtual environment will live inside this folder.

## Installing Dependencies

The `setup.sh` script creates a virtual environment (`venv`) and installs the Python packages from `requirements.txt`. Run it from the project directory:

```bash
bash setup.sh
```

The script can be re-run at any time to upgrade `pip` or reinstall dependencies.

## Running the Application

Once the environment is set up, start the Flask server with:

```bash
bash run.sh
```

Both scripts automatically activate the virtual environment. The main web interface will be available on port 5000 by default.

## Required Services

The optional `db_server.py` utility expects a running MySQL server. Install MySQL on Ubuntu with:

```bash
sudo apt update
sudo apt install mysql-server
```

Create a database named `botmanager` and ensure that the credentials in `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` match your MySQL setup.


## Admin Backend

The project now exposes a simple admin interface under `/admin`. Default credentials are `admin/admin123` which are inserted into the SQLite database on first run. Bots can be uploaded as ZIP archives and are mounted dynamically using `DispatcherMiddleware`.

API endpoints are available under `/api/admin` and return JSON for integration with frontend applications. Only a subset is implemented (login and basic bot management) but the structure is designed to be extended.
