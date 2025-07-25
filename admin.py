import importlib.util
import importlib
from flask import Flask, render_template, request, jsonify, redirect, url_for, Blueprint, session
import os
import shutil
import json
import zipfile
import subprocess
import sys
import psutil
import time
from datetime import datetime
from werkzeug.middleware.dispatcher import DispatcherMiddleware

manager_bp = Blueprint("manager_bp", __name__)

app = Flask(__name__)
app.secret_key = "541cs65g6reghk;tlh3241d65fytxcn"  # Required for session management

# Base paths
BASE_DIR = os.getenv("BOT_MANAGER_HOME", os.path.dirname(os.path.abspath(__file__)))
BASE_PATH = os.path.join(BASE_DIR, "python_scripts")
SCRIPT_DIR = os.path.join(BASE_DIR, "python_scripts")
BACKUP_DIR = os.path.join(BASE_DIR, "python_scripts_backup")
IMAGE_PATH = os.path.join(app.static_folder, "images")
VENV_PATH = os.path.join(BASE_DIR, "venv")
JSON_FILE = os.path.join(BASE_PATH, "buttons.json")
TEMP_EXTRACT_PATH = os.path.join(BASE_PATH, "temp_extract")

os.makedirs(BASE_PATH, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(IMAGE_PATH, exist_ok=True)

@app.before_request
def require_login():
    if request.endpoint not in ('login', 'static') and 'user_logged_in' not in session:
        return redirect(url_for('manager_bp.login'))

@manager_bp.route("/login", methods=["GET", "POST"])
def login():
    cache_version = int(time.time())
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin123":
            session['user_logged_in'] = True
            return redirect(url_for("manager_bp.index"))
        return render_template("login.html", error="Invalid credentials", cache_version=cache_version)
    return render_template("login.html", cache_version=cache_version)

@manager_bp.route("/logout")
def logout():
    session.pop('user_logged_in', None)
    return redirect(url_for('manager_bp.login'))

def create_backup(folder_name):
    """Creates a backup of the specified Python script folder with date and time."""
    script_dir = os.path.join(BASE_PATH, folder_name)
    if not os.path.exists(script_dir):
        print(f"❌ Folder '{folder_name}' not found. Skipping backup.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder_name = f"{folder_name}_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_folder_name)

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    shutil.copytree(script_dir, backup_path)
    print(f"✅ Backup created at: {backup_path}")

def install_requirements(req_path):
    """Install dependencies from a requirements file using pip."""
    script_dir = os.path.dirname(req_path)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_path],
        check=True,
        cwd=script_dir,
    )

def load_buttons():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    return {}

def save_buttons(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

def terminate_process_by_pid(pid):
    """Kill the running process using the stored PID."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
    except psutil.NoSuchProcess:
        print(f"Process with PID {pid} not found.")
    except Exception as e:
        print(f"Failed to terminate PID {pid}: {e}")

def create_button(folder_name):
    buttons_data = load_buttons()
    info = buttons_data.get(folder_name, {})
    return info.get("button_name", folder_name), folder_name, info.get("image", "/static/images/default.png")

@manager_bp.route("/")
def index():
    buttons_data = load_buttons()
    buttons = [(info["button_name"], folder, info["image"]) for folder, info in buttons_data.items()]
    cache_version = int(time.time())
    return render_template("index.html", buttons=buttons, cache_version=cache_version)

@manager_bp.route("/upload", methods=["POST"])
def upload():
    zip_file = request.files["zip_file"]
    image_file = request.files.get("image")
    button_name = request.form.get("button_name", "").strip()

    if zip_file and button_name:
        folder_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in button_name).lower()
        script_dir = os.path.join(BASE_PATH, folder_name)

        if os.path.exists(script_dir):
            print(f"⚠️ Folder '{folder_name}' already exists. Removing existing folder.")
            # Optional: Add backup logic here if you want backup on overwrite too
            # create_backup(folder_name)
            shutil.rmtree(script_dir)
        os.makedirs(script_dir, exist_ok=True)
        print(f"✅ Created script directory: {script_dir}")

        zip_path = os.path.join(BASE_PATH, f"{folder_name}_temp.zip") # Use a temp name
        zip_file.save(zip_path)
        print(f"Saved uploaded zip to: {zip_path}")

        temp_extract_target = os.path.join(BASE_PATH, f"temp_extract_{folder_name}")
        if os.path.exists(temp_extract_target):
            shutil.rmtree(temp_extract_target)
        os.makedirs(temp_extract_target, exist_ok=True)
        print(f"Created temporary extraction directory: {temp_extract_target}")

        # Extract zip with progress tracking (optional, kept from original)
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                total_files = len(zip_ref.infolist())
                print(f"Extracting {total_files} files from zip...")
                for i, file_info in enumerate(zip_ref.infolist()):
                    zip_ref.extract(file_info, temp_extract_target)
                    # Simple progress update, avoid flooding logs too much
                    if (i + 1) % max(1, total_files // 10) == 0 or (i + 1) == total_files:
                         progress = (i + 1) / total_files * 100
                         print(f"Extraction Progress: {progress:.2f}%")
            print(f"✅ Extraction complete.")
        except zipfile.BadZipFile:
            print(f"❌ Error: Uploaded file is not a valid ZIP archive.")
            os.remove(zip_path)
            shutil.rmtree(temp_extract_target)
            shutil.rmtree(script_dir) # Clean up created script dir
            return "Error: Invalid ZIP file provided.", 400
        except Exception as e:
            print(f"❌ Error during zip extraction: {e}")
            os.remove(zip_path)
            shutil.rmtree(temp_extract_target)
            shutil.rmtree(script_dir) # Clean up created script dir
            return f"Error during extraction: {e}", 500
        finally:
             if os.path.exists(zip_path):
                os.remove(zip_path) # Clean up the temporary zip file


        # Handle nested directories within the zip
        extracted_items = os.listdir(temp_extract_target)
        source_dir_for_move = temp_extract_target
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_target, extracted_items[0])):
            # If ZIP contains a single top-level folder, use its content
            source_dir_for_move = os.path.join(temp_extract_target, extracted_items[0])
            print(f"Detected nested folder '{extracted_items[0]}' in ZIP. Using its contents.")

        print(f"Moving files from {source_dir_for_move} to {script_dir}")
        for item in os.listdir(source_dir_for_move):
            shutil.move(os.path.join(source_dir_for_move, item), script_dir)

        # Clean up extraction directory
        shutil.rmtree(temp_extract_target)
        print(f"Cleaned up temporary extraction directory.")

        # Rename the first .py file to main.py
        py_files = [f for f in os.listdir(script_dir) if f.endswith(".py") and f != '__init__.py'] # Exclude __init__.py
        main_py_path = os.path.join(script_dir, "main.py")
        if not os.path.exists(main_py_path) and py_files:
            os.rename(os.path.join(script_dir, py_files[0]), main_py_path)
            print(f"Renamed '{py_files[0]}' to 'main.py'.")
        elif not os.path.exists(main_py_path) and not py_files:
            print("❌ Error: No .py file found in the extracted content.")
            shutil.rmtree(script_dir)
            return "Error: No Python script found in ZIP", 400
        elif os.path.exists(main_py_path):
             print("Found 'main.py'. No rename needed.")


        # --- Install requirements using pip ---
        req_path = os.path.join(script_dir, "requirements.txt")
        if os.path.exists(req_path):
            print(f"Found requirements.txt at {req_path}. Installing dependencies.")
            try:
                install_requirements(req_path)
                print("✅ Dependencies installed.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error installing dependencies: {e}")
                shutil.rmtree(script_dir)
                return "Error installing dependencies", 500
            except Exception as e:
                print(f"❌ Unexpected error installing dependencies: {e}")
                shutil.rmtree(script_dir)
                return "Error installing dependencies", 500
        else:
            print("No requirements.txt found. Skipping dependency installation.")
        # --- End: Install requirements ---

        # Update buttons.json
        buttons_data = load_buttons()
        img_path = "/static/images/default.png" # Default image
        if image_file and image_file.filename: # Check if a file was actually uploaded
            try:
                img_filename = f"{folder_name}.png" # Use folder name for consistency
                image_save_path = os.path.join(IMAGE_PATH, img_filename)
                image_file.save(image_save_path)
                img_path = url_for('static', filename=f'images/{img_filename}') # Use url_for for safety
                print(f"Saved image to: {image_save_path}")
            except Exception as e:
                print(f"⚠️ Warning: Could not save image file: {e}. Using default image.")
                img_path = "/static/images/default.png"

        buttons_data[folder_name] = {"button_name": button_name, "image": img_path}
        save_buttons(buttons_data)
        print(f"Updated buttons.json for '{folder_name}'.")

        # Dynamically register the app
        # IMPORTANT: If new dependencies were installed, registration might still
        # fail within the same running process due to Python's import caching.
        # A restart of the main app might be required.
        print("Attempting to register apps after upload...")
        try:
            register_all_apps()
            print("✅ App registration process completed.")
        except Exception as e:
             print(f"⚠️ Error during dynamic app registration after upload: {e}")
             print("ℹ️ A manual restart of the Flask Bot Manager might be required for the new app to function correctly.")


    else:
        # Handle cases where zip or button name is missing
        if not zip_file:
             print("Upload failed: No ZIP file provided.")
        if not button_name:
             print("Upload failed: Button name was empty.")
        # Consider adding a Flask flash message here for the user
        return redirect(url_for("manager_bp.index")) # Redirect back, maybe with an error message

    return redirect(url_for("manager_bp.index"))

@manager_bp.route("/delete/<folder_name>")
def delete_script(folder_name):
    script_dir = os.path.join(BASE_PATH, folder_name)
    image_path = os.path.join(IMAGE_PATH, f"{folder_name}.png")
    buttons_data = load_buttons()

    if folder_name in buttons_data and "pid" in buttons_data[folder_name]:
        pid = buttons_data[folder_name]["pid"]
        terminate_process_by_pid(pid)
        del buttons_data[folder_name]["pid"]

    # Unregister blueprint and clean up sys.modules
    if folder_name in app.blueprints:
        app.blueprints.pop(folder_name, None)
    mod_name = f"{folder_name}_app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    time.sleep(0.5)

    # Create backup before deletion
    create_backup(folder_name)

    try:
        if os.path.exists(script_dir):
            shutil.rmtree(script_dir)
        if os.path.exists(image_path):
            os.remove(image_path)
        if folder_name in buttons_data:
            del buttons_data[folder_name]
        save_buttons(buttons_data)

        return jsonify({"status": "success", "message": f"Deleted '{folder_name}'"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@manager_bp.route("/edit/<folder_name>", methods=["POST"])
def edit_script(folder_name):
    new_button_name = request.form.get("button_name", "").strip()
    new_zip_file = request.files.get("zip_file")
    new_image_file = request.files.get("image")

    original_script_dir = os.path.join(BASE_PATH, folder_name) # Keep original path for checks/backup
    buttons_data = load_buttons()

    if folder_name not in buttons_data:
        return jsonify({"status": "error", "message": "App not found."}), 404

    # --- Prepare for update ---
    # Terminate existing process if running (PID logic - keep as is)
    if "pid" in buttons_data[folder_name]:
        pid = buttons_data[folder_name]["pid"]
        print(f"Attempting to terminate running process PID: {pid} for app '{folder_name}' before edit.")
        terminate_process_by_pid(pid)
        # Remove PID regardless of termination success, as the code is changing
        del buttons_data[folder_name]["pid"]
        # Save button data immediately after removing PID
        save_buttons(buttons_data)

    # Unregister blueprint/module (keep as is)
    if folder_name in app.blueprints:
        app.blueprints.pop(folder_name, None)
    mod_name = f"{folder_name}_app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    time.sleep(0.5) # Allow time for resources to release

    # Create backup before making changes (keep as is)
    print(f"Creating backup for '{folder_name}' before editing.")
    create_backup(folder_name)

    # --- Apply Changes ---
    script_dir = os.path.join(BASE_PATH, folder_name) # Use consistent variable name

    # If new ZIP is uploaded, replace the entire script directory content
    if new_zip_file and new_zip_file.filename:
        print(f"New ZIP file provided for '{folder_name}'. Replacing content.")
        # Remove existing script directory content
        if os.path.exists(script_dir):
            shutil.rmtree(script_dir)
        os.makedirs(script_dir, exist_ok=True)

        # Save and extract the new zip (similar logic to upload)
        zip_path = os.path.join(BASE_PATH, f"{folder_name}_temp_edit.zip")
        new_zip_file.save(zip_path)
        print(f"Saved uploaded zip for edit to: {zip_path}")

        temp_extract_target = os.path.join(BASE_PATH, f"temp_extract_edit_{folder_name}")
        if os.path.exists(temp_extract_target):
            shutil.rmtree(temp_extract_target)
        os.makedirs(temp_extract_target, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                print(f"Extracting new zip file for '{folder_name}'...")
                zip_ref.extractall(temp_extract_target)
                print(f"✅ Extraction complete.")
        except Exception as e:
            print(f"❌ Error extracting new zip for edit: {e}")
            if os.path.exists(zip_path): os.remove(zip_path)
            if os.path.exists(temp_extract_target): shutil.rmtree(temp_extract_target)
            # Optionally restore from backup here if needed, or just fail
            return jsonify({"status": "error", "message": f"Failed to extract new ZIP: {e}"}), 500
        finally:
             if os.path.exists(zip_path): os.remove(zip_path)

        # Handle nested dir in new zip
        extracted_items = os.listdir(temp_extract_target)
        source_dir_for_move = temp_extract_target
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_target, extracted_items[0])):
            source_dir_for_move = os.path.join(temp_extract_target, extracted_items[0])

        print(f"Moving new files from {source_dir_for_move} to {script_dir}")
        for item in os.listdir(source_dir_for_move):
            shutil.move(os.path.join(source_dir_for_move, item), script_dir)
        shutil.rmtree(temp_extract_target)

        # Rename to main.py if necessary
        py_files = [f for f in os.listdir(script_dir) if f.endswith(".py") and f != '__init__.py']
        main_py_path = os.path.join(script_dir, "main.py")
        if not os.path.exists(main_py_path) and py_files:
             try:
                os.rename(os.path.join(script_dir, py_files[0]), main_py_path)
                print(f"Renamed '{py_files[0]}' to 'main.py'.")
             except Exception as e:
                 print(f"❌ Error renaming python file to main.py: {e}")
                 # Decide how critical this is - maybe return error?
        elif not os.path.exists(main_py_path) and not py_files:
            print(f"❌ Error: No .py file found in the new ZIP for '{folder_name}'.")
            # Cleanup potentially broken state? Or rely on user to fix.
            return jsonify({"status": "error", "message": "No Python script found in new ZIP."}), 400

        # --- Install requirements using pip ---
        req_path = os.path.join(script_dir, "requirements.txt")
        if os.path.exists(req_path):
            print(f"Found requirements.txt in new ZIP for '{folder_name}'. Installing dependencies.")
            try:
                install_requirements(req_path)
                print("✅ Dependencies installed for edited app.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error installing dependencies for edited '{folder_name}': {e}")
                return jsonify({"status": "error", "message": f"Failed to install dependencies from new ZIP: {e}"}), 500
            except Exception as e:
                print(f"❌ Unexpected error installing dependencies for edited '{folder_name}': {e}")
                return jsonify({"status": "error", "message": f"Failed to install dependencies from new ZIP: {e}"}), 500
        else:
             print(f"No requirements.txt found in new ZIP for '{folder_name}'. Skipping dependency installation.")
        # --- End install requirements ---

    # --- Update metadata (Image and Button Name) ---
    buttons_data = load_buttons() # Reload data in case it changed
    if folder_name not in buttons_data: # Should exist, but check again
         buttons_data[folder_name] = {} # Initialize if somehow missing

    # Update image if a new one was uploaded
    if new_image_file and new_image_file.filename:
        try:
            img_filename = f"{folder_name}.png"
            image_save_path = os.path.join(IMAGE_PATH, img_filename)
            # Remove old image first? Optional.
            if os.path.exists(image_save_path):
                os.remove(image_save_path)
            new_image_file.save(image_save_path)
            buttons_data[folder_name]["image"] = url_for('static', filename=f'images/{img_filename}')
            print(f"Updated image for '{folder_name}'.")
        except Exception as e:
            print(f"⚠️ Warning: Could not save new image file during edit: {e}.")
            # Keep existing image path if save fails

    # Update button name if a new one was provided
    if new_button_name:
        buttons_data[folder_name]["button_name"] = new_button_name
        print(f"Updated button name for '{folder_name}' to '{new_button_name}'.")

    # Ensure essential keys exist even if only image/name was updated
    if "button_name" not in buttons_data[folder_name]:
         buttons_data[folder_name]["button_name"] = folder_name # Default if missing
    if "image" not in buttons_data[folder_name]:
         buttons_data[folder_name]["image"] = "/static/images/default.png" # Default if missing

    save_buttons(buttons_data) # Save all accumulated changes

    # --- Finalize ---
    print(f"Attempting to register apps after editing '{folder_name}'...")
    try:
        register_all_apps() # Re-register to load the updated app
        print("✅ App registration process completed after edit.")
    except Exception as e:
         print(f"⚠️ Error during dynamic app registration after edit: {e}")
         print("ℹ️ A manual restart of the Flask Bot Manager might be required for the edited app to function correctly.")

    return jsonify({"status": "success", "message": "App updated successfully"})

def load_uploaded_app(folder_name):
    """Load an app's main.py from the folder and return its Flask instance."""
    script_dir = os.path.join(BASE_PATH, folder_name)
    main_script = os.path.join(script_dir, "main.py")

    if not os.path.exists(main_script):
        print(f"⚠️ main.py not found in {script_dir}")
        return None

    print(f"Attempting to invalidate import caches before loading {folder_name}_app...")
    importlib.invalidate_caches()

    spec = importlib.util.spec_from_file_location(f"{folder_name}_app", main_script)
    if spec is None or spec.loader is None:
         print(f"❌ Could not create module spec for {main_script}")
         return None

    module = importlib.util.module_from_spec(spec)
    # Crucially, register the module *before* modifying sys.path if possible,
    # although exec_module is where the import happens.
    sys.modules[spec.name] = module

    # --- Temporarily modify sys.path ---
    original_sys_path = list(sys.path) # Make a copy
    path_added = False
    if script_dir not in sys.path:
        print(f"Adding '{script_dir}' to sys.path for module execution.")
        sys.path.insert(0, script_dir) # Add to the beginning
        path_added = True
    # --- End temporary modification ---

    try:
        print(f"Executing module: {spec.name}")
        print(f"DEBUG: sys.path before exec_module for {spec.name}: {sys.path}")
        # This is where imports inside main.py (like 'import utils') happen
        spec.loader.exec_module(module)
        print(f"✅ Successfully executed module: {spec.name}")
    except ImportError as e: # Catch ImportError specifically now
        print(f"❌ ImportError during exec_module for {spec.name}: {e}")
        # Check if it's the utils import again or something else
        if 'utils' in str(e):
             print(f"Checklist: Does '{os.path.join(script_dir, 'utils')}' exist? Does it contain '__init__.py'?")
        print(f"Current sys.path: {sys.path}")
        if spec.name in sys.modules: del sys.modules[spec.name]
        module = None # Failed to load
    except Exception as e:
        print(f"❌ Unexpected error during exec_module for {spec.name}: {e}")
        if spec.name in sys.modules: del sys.modules[spec.name]
        module = None # Failed to load
    finally:
        # --- Restore original sys.path ---
        if path_added: # Only restore if we actually added it
            print(f"Restoring original sys.path.")
            sys.path = original_sys_path
        # --- End restore ---

    # Return the Flask app instance if available *and* module loaded successfully
    if module and hasattr(module, "app"):
        return module.app
    elif module:
        print(f"⚠️ Module {spec.name} loaded but has no 'app' attribute.")
        return None
    else:
        # Module loading failed in the except block
        return None

def register_all_apps():
    """Register all apps dynamically using DispatcherMiddleware."""
    mapping = {}

    for folder in os.listdir(BASE_PATH):
        script_dir = os.path.join(BASE_PATH, folder)
        if os.path.isdir(script_dir) and os.path.exists(os.path.join(script_dir, "main.py")):
            uploaded_app = load_uploaded_app(folder)
            if uploaded_app:
                mapping[f"/{folder}"] = uploaded_app
            else:
                print(f"⚠️ Failed to load app for {folder}")

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, mapping)

if __name__ == "__main__":
    app.register_blueprint(manager_bp, url_prefix="/")
    register_all_apps()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
