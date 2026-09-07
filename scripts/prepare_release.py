"""Check materialized source and fix explicit test-connection cleanup."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ['README.md', 'project.json', 'app/service.py', 'app/advanced.py', 'localdesk/vault.py', 'run.py', 'web/app.js']:
        if not (ROOT / name).is_file():
            raise ValueError('Required source is absent: ' + name)
    path = ROOT / 'tests/test_upgrade.py'
    text = path.read_text(encoding='utf-8')
    old = ['with sqlite3.connect(p) as db:', 'with sqlite3.connect(q) as db:']
    if any(value in text for value in old):
        if any(text.count(value) != 1 for value in old):
            raise ValueError('Review the changed database regression test.')
        text = text.replace('import sqlite3\n', 'import sqlite3\nfrom contextlib import closing\n')
        text = text.replace(old[0], 'with closing(sqlite3.connect(p)) as db, db:')
        text = text.replace(old[1], 'with closing(sqlite3.connect(q)) as db, db:')
        path.write_text(text, encoding='utf-8')
    shutil.rmtree(ROOT / '_runtime', ignore_errors=True)
    print('Source checked. Test connections close before temporary files are removed.')


if __name__ == '__main__':
    main()
