"""Configurações específicas do Bhadrasana."""
import os
import tempfile

from ajna_commons.conf import ENCODE

ENCODE = ENCODE

APP_PATH = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_PATH, 'files')
CSV_FOLDER = os.path.join(APP_PATH, 'CSV')
CSV_DOWNLOAD = CSV_FOLDER
CSV_FOLDER_TEST = os.path.join(APP_PATH, 'tests/CSV')
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'zip'])
tmpdir = tempfile.mkdtemp()
