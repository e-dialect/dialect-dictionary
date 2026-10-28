"""Initialize only this Compose project's isolated volume, then serve Django."""
import os
import secrets
import subprocess
import sys
from pathlib import Path

data = Path(os.environ.get("DICTIONARY_DATA_DIR", "/data"))
data.mkdir(parents=True, exist_ok=True)
for variable in ("SECRET_KEY", "JWT_KEY"):
    if not os.environ.get(variable):
        path = data / ("." + variable.lower())
        if not path.exists():
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(secrets.token_urlsafe(48))
        os.environ[variable] = path.read_text().strip()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HinghwaDict.standalone")
subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput", "--verbosity", "0"], check=True)
if os.environ.get("DICTIONARY_SEED_DEMO") == "1":
    subprocess.run([sys.executable, "manage.py", "seed_dictionary_demo"], check=True)
os.execvp("gunicorn", ["gunicorn", "HinghwaDict.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "60", "--access-logfile", "-"])
