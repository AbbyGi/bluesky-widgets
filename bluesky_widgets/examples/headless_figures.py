"""
Use within IPython like

ipython --gui=qt

In [1]: %run -m bluesky_widgets.examples.ipy_qt_figures
"""
import tempfile

from bluesky import RunEngine
from bluesky.plans import scan
from ophyd.sim import motor, det

from bluesky_widgets.utils.streaming import stream_documents_into_runs
from bluesky_widgets.models.plot_builders import AutoRecentLines
from bluesky_widgets.headless.figures import HeadlessFigures
from bluesky_widgets.examples.utils.generate_msgpack_data import get_catalog

model = AutoRecentLines(3)
view = HeadlessFigures(model.figures)

RE = RunEngine()
RE.subscribe(stream_documents_into_runs(model.add_run))


catalog = get_catalog()
scans = catalog.search({"plan_name": "scan"})
model.add_run(scans[-1], pinned=True)


def plan():
    for i in range(1, 5):
        yield from scan([det], motor, -1, 1, 1 + 2 * i)


RE(plan())


directory = tempfile.mkdtemp()
filenames = view.export_all(directory)
print("Figures exported:")
print("\n".join(f'"{filename}"' for filename in filenames))
