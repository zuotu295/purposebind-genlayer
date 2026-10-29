"""Share the official linter's pinned artifact with the Direct Mode runner."""
from pathlib import Path
import shutil
name='genvm-universal-v0.3.0-rc7.tar.xz'
source=Path.home()/'.cache/genvm-linter'/name
target=Path.home()/'.cache/gltest-direct'/name
if not source.exists():
    raise SystemExit('Run genvm-lint check contracts/purpose_bind.py first.')
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists(): shutil.copyfile(source,target)
print('Pinned SDK artifact ready.')
