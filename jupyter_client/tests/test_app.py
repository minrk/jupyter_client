"""Test application entrypoints"""

import os
import signal
from subprocess import check_output, Popen, PIPE, STDOUT
import sys
import time

from ..kernelapp import KernelApp
from ..kernelspec import NATIVE_KERNEL_NAME

jupyter_kernel = [sys.executable, '-m', 'jupyter', 'kernel']

def test_help_all():
    out = check_output(jupyter_kernel + ['--help-all'])


def test_default_kernel():
    app = KernelApp()
    assert app.kernel_name == NATIVE_KERNEL_NAME


def test_signal():
    p = Popen(jupyter_kernel + ['--kernel=%s' % NATIVE_KERNEL_NAME],
              stdout=PIPE, stderr=STDOUT)
    cf = None
    while p.poll() is None:
        line = p.stdout.readline().decode('utf8', 'replace')
        if 'Connection file' in line:
            cf = line.split(':', 1)[1].strip()
            break
    assert cf is not None
    assert os.path.exists(cf)
    time.sleep(1)
    p.send_signal(signal.SIGINT)
    p.wait()
    # ensure cleanup happened
    assert not os.path.exists(cf)
