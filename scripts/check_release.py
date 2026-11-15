"""Release preflight: reject embedded credentials and private/generated source files.
Run before committing. Does not print secret values or contact external services.
"""
import ast
from pathlib import Path
import subprocess
import sys

FIELDS = {'appid', 'secret_key', 'app_key', 'app_secret'}
PRIVATE_PARTS = {'.git', '.venv', '.claude', 'artifacts', 'build', 'dist', '__pycache__'}


def config_errors(path):
    errors = []
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or key.value not in FIELDS:
                continue
            valid = (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                     and value.func.attr == 'get' and isinstance(value.func.value, ast.Attribute)
                     and value.func.value.attr == 'environ' and isinstance(value.func.value.value, ast.Name)
                     and value.func.value.value.id == 'os' and len(value.args) == 2
                     and isinstance(value.args[0], ast.Constant)
                     and isinstance(value.args[0].value, str)
                     and isinstance(value.args[1], ast.Constant) and value.args[1].value == '')
            if not valid:
                errors.append(f'config.py:{key.lineno}: credential {key.value} must use an empty environment-variable default')
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    errors = config_errors(root / 'config.py')
    git = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True)
    paths = [Path(p) for p in git.stdout.decode('utf-8').split('\0') if p] if git.returncode == 0 else [
        p.relative_to(root) for p in root.rglob('*') if p.is_file() and not PRIVATE_PARTS.intersection(p.relative_to(root).parts)
    ]
    for path in paths:
        if (PRIVATE_PARTS.intersection(path.parts) or path.suffix.lower() in {'.db', '.log', '.exe', '.zip', '.pyc'}
                or (path.name.startswith('.env') and path.name != '.env.example')):
            errors.append(f'Private/generated file tracked: {path.as_posix()}')
    # Local migration preflight can optionally compare against current-user values,
    # which never leave this process or get printed.
    if '--compare-local-credentials' in sys.argv:
        import winreg
        values = []
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as registry:
                for name in ('BAIDU_APPID', 'BAIDU_SECRET_KEY'):
                    try:
                        value, _ = winreg.QueryValueEx(registry, name)
                        if value:
                            values.append(value.encode('utf-8'))
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass
        for path in paths:
            file = root / path
            if file.is_file() and any(secret in file.read_bytes() for secret in values):
                errors.append(f'Configured credential found in candidate file: {path.as_posix()}')
        executable = root / 'dist' / 'TranslateAssistant.exe'
        if executable.is_file():
            from PyInstaller.archive.readers import CArchiveReader
            bundled = CArchiveReader(str(executable)).extract('config.py')
            if any(secret in bundled for secret in values):
                errors.append('Configured credential found in bundled config.py')
            else:
                print('PASS: executable configuration contains no current-user credential literals')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'PASS: configuration and {len(paths)} candidate source files checked; no private/generated files tracked')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
