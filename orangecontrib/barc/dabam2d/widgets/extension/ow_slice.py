"""Extract a line cut from an OASYS height map."""

from pathlib import Path

import h5py
import numpy
from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import QFormLayout, QLabel, QScrollArea, QSplitter
from orangewidget import gui
from orangewidget.settings import Setting
from orangewidget.widget import Input, Output
from silx.gui.plot import Plot1D

from dabam2d.processing import slice_surface
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui
from oasys2.widget.util.widget_objects import OasysSurfaceData
from oasys2.widget.widget import OWWidget
from orangecontrib.shadow4.util.python_script import PythonScript

from ...utils.surface_recipe import HeightCutData, Operation, SurfaceRecipe


class OWDabam2DSlice(OWWidget):
    name = "Slice"
    id = "barc_dabam2d_slice"
    description = "Extract an interpolated 1D profile from a surface"
    icon = "icons/slice.png"
    priority = 2
    keywords = ["dabam2d", "surface", "slice", "profile"]

    class Inputs:
        surface_data = Input("Surface Data", OasysSurfaceData, auto_summary=False)

    class Outputs:
        dabam_profile = Output("DABAM 1D Profile", numpy.ndarray, default=True, auto_summary=False)
        height_cut = Output("Height Cut", HeightCutData, auto_summary=False)

    CONTROL_AREA_WIDTH = 370
    FIELD_WIDTH = 130
    direction = Setting(0)
    position = Setting(0.0)

    def __init__(self):
        super().__init__()
        self._surface = None
        self._recipe = None

        self.controlArea.setMinimumWidth(self.CONTROL_AREA_WIDTH - 40)
        sidebar = self.controlArea
        while sidebar.parentWidget() is not None and sidebar.parentWidget() is not self:
            if isinstance(sidebar, QScrollArea) or isinstance(sidebar.parentWidget(), QSplitter):
                sidebar.setMinimumWidth(self.CONTROL_AREA_WIDTH)
                break
            sidebar = sidebar.parentWidget()

        controls = oasysgui.widgetBox(self.controlArea, "Slice")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        controls.layout().addLayout(form)

        direction_field = oasysgui.widgetBox(None, orientation="horizontal")
        direction = gui.comboBox(
            direction_field, self, "direction", items=["Horizontal", "Vertical"],
            orientation="horizontal", callback=self._update_cut,
        )
        direction.setFixedWidth(self.FIELD_WIDTH)
        form.addRow("Direction", direction_field)

        position_field = oasysgui.widgetBox(None, orientation="horizontal")
        oasysgui.lineEdit(
            position_field, self, "position", valueType=float, controlWidth=self.FIELD_WIDTH,
            orientation="horizontal", callback=self._update_cut,
        )
        form.addRow("At coordinate [m]", position_field)
        self._status = QLabel("No surface connected", self.controlArea)
        self._status.setWordWrap(True)
        self.controlArea.layout().addWidget(self._status)
        gui.rubber(self.controlArea)

        tabs = oasysgui.tabWidget(self.mainArea)
        profile_tab = oasysgui.createTabPage(tabs, "Profile")
        self._plot = Plot1D()
        profile_tab.layout().addWidget(self._plot)
        script_tab = oasysgui.createTabPage(tabs, "Python Script")
        self._script = PythonScript()
        script_tab.layout().addWidget(self._script)
        self._script.set_code("# Connect a surface to generate the script.\n")

    @Inputs.surface_data
    def set_surface_data(self, data):
        self._surface = None
        self._recipe = None
        if data is not None:
            self._recipe = getattr(data, "recipe", None)
            self._surface = {"x": data.xx, "y": data.yy, "z": data.zz}
            if self._recipe is None or any(value is None for value in self._surface.values()):
                path, saved_surface = _legacy_surface(data.surface_data_file)
                if self._recipe is None:
                    self._recipe = SurfaceRecipe(source_path=path, legacy=True)
                if any(value is None for value in self._surface.values()):
                    self._surface = saved_surface
        self._update_cut()

    def _update_cut(self):
        self._plot.clear()
        if self._surface is None:
            self._clear_cut("No surface connected" if self._recipe is None else "Surface data unavailable")
            return

        direction = ("h", "v")[self.direction]
        try:
            cut = slice_surface(self._surface, direction, self.position)
        except (TypeError, ValueError) as error:
            self._clear_cut(str(error))
            return

        position = cut["position"]
        axis_label, fixed_axis = ("X", "Y") if direction == "h" else ("Y", "X")
        self._plot.addCurve(cut["axis"], cut["profile"], legend="Height")
        self._plot.setGraphXLabel(f"{axis_label} [m]")
        self._plot.setGraphYLabel("Height [m]")
        self._plot.setGraphTitle(f"Cut at {fixed_axis} = {position:g} m")
        self._plot.resetZoom()
        self._status.setText(f"{cut['axis'].size} samples · {numpy.isnan(cut['profile']).sum()} NaNs")

        recipe = self._recipe.append(
            Operation("slice_surface", (("direction", direction), ("position", position)), result="cut")
        )
        self._script.set_code(recipe.python_script())
        self.Outputs.dabam_profile.send(numpy.column_stack((cut["axis"], cut["profile"])))
        self.Outputs.height_cut.send(HeightCutData(cut=cut, recipe=recipe))

    def _clear_cut(self, message):
        self._status.setText(message)
        if self._recipe is not None and self._recipe.legacy and self._recipe.source_path is None:
            script = self._recipe.python_script()
        else:
            script = f"# {message}\n"
        self._script.set_code(script)
        self.Outputs.dabam_profile.send(None)
        self.Outputs.height_cut.send(None)


def _legacy_surface(file_path):
    if file_path:
        path = Path(file_path).expanduser().absolute()
        try:
            with h5py.File(path, "r") as file:
                group = file["surface_file"]
                surface = {key.lower(): group[key][()] for key in "XYZ"}
            return str(path), surface
        except (OSError, KeyError, TypeError, ValueError):
            pass
    return None, None


add_widget_parameters_to_module(__name__)
