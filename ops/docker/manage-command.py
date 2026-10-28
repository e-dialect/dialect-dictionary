"""Management commands reuse existing private keys; never create keys or migrate implicitly."""
import os
from pathlib import Path
import runpy
import sys

data = Path(os.environ.get('DICTIONARY_DATA_DIR', '/data'))
for variable in ('SECRET_KEY', 'JWT_KEY'):
    if not os.environ.get(variable):
        path = data / ('.' + variable.lower())
        if not path.is_file():
            raise SystemExit('实例尚未初始化：请先 ./dictionary start；管理命令不自行创建密钥。')
        os.environ[variable] = path.read_text().strip()
sys.argv = ['manage.py'] + sys.argv[1:]
runpy.run_path('/app/manage.py', run_name='__main__')
