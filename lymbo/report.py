import glob
import os
import tempfile

from lymbo.env import LYMBO_REPORT_PATH


class TestReport:

    def __init__(self, path=None):
        if path is None:
            path = tempfile.mkdtemp()
        else:
            os.makedirs(path, exist_ok=True)
        self.path = path

        os.environ[LYMBO_REPORT_PATH] = str(self.path)

        self.clean()

    def clean(self):

        for lymbofile in glob.glob(os.path.join(self.path, "lymbo-*")):
            os.remove(lymbofile)
