#!/usr/bin/env python3
"""Stop only the good lab3 stack, using its saved manifest and private env file."""
import subprocess
from ci import STATE, compose_args, load, pipeline_lock

with pipeline_lock():
    release = load(STATE / 'current.json')
    if not release:
        raise SystemExit('No saved deployment manifest; nothing was stopped')
    args, env = compose_args(release)
    subprocess.run([str(value) for value in args] + ['stop'], env=env, check=True)
