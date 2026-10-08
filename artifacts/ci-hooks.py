from pathlib import Path
import os, subprocess, sys, tempfile, yaml
root=Path.cwd()
action=yaml.safe_load((root/'.github/actions/setup-test-env/action.yml').read_text())
body=action['runs']['steps'][0]['run'].split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
with tempfile.TemporaryDirectory() as folder:
 env_file=Path(folder)/'github-env'
 env={**os.environ,'GITHUB_ENV':str(env_file)}
 result=subprocess.run([sys.executable,'-c',body],env=env,capture_output=True,text=True,check=True)
 values=dict(line.split('=',1) for line in env_file.read_text().splitlines())
 assert len(values['SECRET_KEY'])>=32 and values['POSTGRES_PASSWORD'] in values['DATABASE_URL']
 env.update(values)
 print('CI environment bootstrap: PASS (disposable credentials, no .env mutation)')
 code="import ast,json,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('app').rglob('*.py')]; import app.main; pathlib.Path('../frontend/openapi.json').write_text(json.dumps(app.main.app.openapi()),encoding='utf-8'); print('Python 3.11 import and OpenAPI: PASS')"
 subprocess.run([sys.executable,'-c',code],cwd=root/'backend',env=env,check=True)
 env['PATH']=r'C:\Program Files\Git\bin'+os.pathsep+env['PATH']
 for cmd in [[str(root/'.venv/Scripts/prek.exe'),'run','--all-files','--show-diff-on-failure']]:
  subprocess.run(cmd,env=env,check=True)
