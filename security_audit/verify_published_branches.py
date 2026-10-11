"""Verify frozen published security heads with an exact per-branch virtual index."""
import json,pathlib,subprocess,os,re,sys
def git(*args):
 p=subprocess.run(['git',*args],capture_output=True,timeout=180)
 if p.returncode:raise RuntimeError('Git verification operation failed')
 return p.stdout
manifest=json.loads(pathlib.Path('security_audit/published_branch_heads.json').read_text())
branches=manifest['branches'];default=manifest['default_ref']
heads={b['ref']:(os.environ['GITHUB_SHA'] if b['ref']==default else b['head']) for b in branches}
if any(not ref.startswith('refs/heads/') or not re.fullmatch('[0-9a-f]{40}',oid) for ref,oid in heads.items()):raise RuntimeError('Invalid verification manifest')
def live():return {line.split()[1]:line.split()[0] for line in git('ls-remote','--heads','origin').decode().splitlines()}
before=live()
if any(before.get(ref)!=oid for ref,oid in heads.items()):raise RuntimeError('Live branch changed since verification preparation')
git('fetch','--no-tags','origin','+refs/heads/*:refs/security-verification/*')
audit=pathlib.Path('.git/security-verification');audit.mkdir(exist_ok=True);results=[]
guard=pathlib.Path('security_audit/secret_scan_sqlite.py').resolve()
os.environ['GIT_INDEX_FILE']=str((audit/'branch.index').resolve())
for ref,head in heads.items():
 base=git('rev-parse',head+'^').strip().decode();git('update-ref','--no-deref','HEAD',base);git('read-tree',head)
 indexed=len([x for x in git('ls-files','--full-name','--stage','-z','--',':/').split(b'\0') if x])
 if indexed<4:raise RuntimeError('Unexpected incomplete branch index')
 config=audit/'gitleaks.toml';config.write_bytes(git('show',head+':.gitleaks.toml'))
 leak=subprocess.run([os.environ.get('GITLEAKS_EXECUTABLE','./gitleaks'),'git','.','--pre-commit','--staged','--redact=100','--no-banner','--config',str(config),'--log-level','error'],capture_output=True,timeout=180)
 database=subprocess.run([sys.executable,str(guard)],capture_output=True,timeout=180)
 passed=leak.returncode==0 and not re.search(rb'(?i)(\bERR\b|FATAL|FTL)',leak.stderr) and database.returncode==0
 row={'ref':ref,'head':head,'indexed_paths':indexed,'status':'PASS' if passed else 'FAILED'};results.append(row);print(json.dumps(row),flush=True)
 if not passed:raise RuntimeError('Security verification failed for '+ref)
after=live()
if any(after.get(ref)!=oid for ref,oid in heads.items()):raise RuntimeError('Live branch changed during verification')
print('ALL_PUBLISHED_BRANCHES_VERIFIED '+json.dumps(results),flush=True)
