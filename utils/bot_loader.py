import importlib.util
import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask


def load_bot(path: str):
    main_py = os.path.join(path, 'main.py')
    if not os.path.exists(main_py):
        return None
    spec = importlib.util.spec_from_file_location(os.path.basename(path) + '_app', main_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, 'app', None)


def register_bots(app: Flask, base_path: str):
    mapping = {}
    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, 'main.py')):
            bot_app = load_bot(folder_path)
            if bot_app:
                mapping[f'/{folder}'] = bot_app
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, mapping)
