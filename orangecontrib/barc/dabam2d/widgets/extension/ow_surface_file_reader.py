"""Load, preview, and save a single DABAM2D surface."""

from pathlib import Path

import numpy
from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel, QMessageBox, QScrollArea, QSplitter, QVBoxLayout
from matplotlib.figure import Figure
from orangewidget import gui
from orangewidget.settings import Setting
from silx.gui.colors import Colormap
from silx.gui.plot import Plot2D

from dabam2d import io, processing
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui
from oasys2.widget.gui import FigureCanvas3D
from oasys2.widget.widget import OWWidget
from orangecontrib.shadow4.util.python_script import PythonScript


class OWDabam2DSurfaceFileReader(OWWidget):
    name = "Surface File Reader"
    id = "barc_dabam2d_surface_file_reader"
    description = "Read and adjust a single metrology height map"
    icon = "icons/raw.png"
    priority = 1
    keywords = ["dabam2d", "metrology", "height", "surface"]

    CONTROL_AREA_WIDTH = 370
    NUMBER_WIDTH = 90

    file_path = Setting("")
    height_scale = Setting(1.0)
    axes_scale = Setting(1.0)
    fill_nans = Setting(False)
    fill_radius = Setting(2)
    subtract_minimum = Setting(False)
    transpose = Setting(False)
    flip_x = Setting(False)
    flip_y = Setting(False)
    rotate = Setting(False)
    angle_deg = Setting(0.0)
    output_path = Setting("")

    def __init__(self):
        super().__init__()
        self._loaded_surface = None
        self._adjusted_surface = None

        self.controlArea.setMinimumWidth(self.CONTROL_AREA_WIDTH - 40)
        # Reserve space on the sidebar container too. Otherwise Qt can
        # clip the controls inside the scroll area when resizing the splitter.
        sidebar = self.controlArea
        while sidebar.parentWidget() is not None and sidebar.parentWidget() is not self:
            if isinstance(sidebar, QScrollArea) or isinstance(sidebar.parentWidget(), QSplitter):
                sidebar.setMinimumWidth(self.CONTROL_AREA_WIDTH)
                break
            sidebar = sidebar.parentWidget()

        input_box = oasysgui.widgetBox(self.controlArea, "Input")
        input_form = self._form(input_box)
        input_form.addRow("File path", self._path_field("file_path", self._input_changed, self._select_input))
        for setting, label in (("height_scale", "Height scaling"), ("axes_scale", "Coordinate scaling")):
            field = oasysgui.widgetBox(None, orientation="horizontal")
            self._number(field, setting, None, float, self._scaling_changed)
            gui.rubber(field)
            input_form.addRow(label, field)
        gui.button(input_box, self, "Load", callback=self.load_surface, autoDefault=False)

        adjustments = oasysgui.widgetBox(self.controlArea, "Basic Adjustments")
        fill_row = oasysgui.widgetBox(adjustments, orientation="horizontal")
        gui.checkBox(fill_row, self, "fill_nans", "Fill NaNs (radius in pixel)", callback=self._adjustments_changed)
        gui.rubber(fill_row)
        self._radius_edit = self._number(
            fill_row, "fill_radius", None, int, self._adjustments_changed,
        )
        for setting, label in (
            ("subtract_minimum", "Subtract minimum height"),
            ("transpose", "Transpose"),
            ("flip_x", "Flip X"),
            ("flip_y", "Flip Y"),
        ):
            gui.checkBox(adjustments, self, setting, label, callback=self._adjustments_changed)
        rotation_row = oasysgui.widgetBox(adjustments, orientation="horizontal")
        gui.checkBox(rotation_row, self, "rotate", "Rotation (degrees)", callback=self._adjustments_changed)
        gui.rubber(rotation_row)
        self._rotation_edit = self._number(
            rotation_row, "angle_deg", None, float, self._adjustments_changed,
        )

        preview = oasysgui.widgetBox(self.controlArea, "Preview")
        self._render_button = gui.button(preview, self, "Preview Surface", callback=self.render_surface, autoDefault=False)

        output = oasysgui.widgetBox(self.controlArea, "Output")
        self._form(output).addRow(
            "File path", self._path_field("output_path", self._update_script, self._select_output)
        )
        self._save_button = gui.button(output, self, "Save as DABAM2D", callback=self.save_surface, autoDefault=False)

        self._summary = QLabel("No surface loaded", self.controlArea)
        self.controlArea.layout().addWidget(self._summary)
        gui.rubber(self.controlArea)

        self._tabs = oasysgui.tabWidget(self.mainArea)
        self._image_tab = oasysgui.createTabPage(self._tabs, "Image")
        self._image = Plot2D()
        self._image.setDefaultColormap(Colormap(name="temperature"))
        self._image.setKeepDataAspectRatio(False)
        self._image.getMaskAction().setVisible(False)
        self._image.getRoiAction().setVisible(False)
        self._image_tab.layout().addWidget(self._image)

        script_tab = oasysgui.createTabPage(self._tabs, "Python Script")
        self._script = PythonScript()
        script_tab.layout().addWidget(self._script)
        self._input_changed()

    @staticmethod
    def _form(parent):
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        parent.layout().addLayout(form)
        return form

    def _number(self, parent, setting, label, value_type, callback):
        return oasysgui.lineEdit(
            parent, self, setting, label, valueType=value_type,
            orientation="horizontal", callback=callback, controlWidth=self.NUMBER_WIDTH,
        )

    def _path_field(self, setting, callback, browse):
        row = oasysgui.widgetBox(None, orientation="horizontal")
        oasysgui.lineEdit(row, self, setting, callback=callback)
        gui.button(row, self, "…", callback=browse, width=30, autoDefault=False)
        return row

    def _select_input(self):
        path = oasysgui.selectFileFromDialog(
            self, self.file_path, "Select Metrology File",
            file_extension_filter="Metrology Files (*.h5 *.hdf5 *.hdf *.dat *.datx *.xyz *.txt);;All Files (*)",
        )
        if path != self.file_path:
            self.file_path = path
            self._input_changed()

    def _input_changed(self):
        self._loaded_surface = None
        self._adjustments_changed()

    def _scaling_changed(self):
        if self._loaded_surface is None:
            self._update_script()
        else:
            self._load_surface()

    def _adjustments_changed(self):
        self._adjusted_surface = None
        self._radius_edit.setEnabled(self.fill_nans)
        self._rotation_edit.setEnabled(self.rotate)
        self._update_script()
        self._image.clear()
        if self._loaded_surface is None:
            self._summary.setText("No surface loaded")
            self._set_preview_actions(False)
            return

        try:
            self._draw_image(self._current_surface())
        except Exception as error:
            self._summary.setText("Preview unavailable")
            self._set_preview_actions(False)
            self._show_error(error)
        else:
            self._set_preview_actions(True)

    def _set_preview_actions(self, enabled):
        self._render_button.setEnabled(enabled)
        self._save_button.setEnabled(enabled)

    def _operations(self):
        """Return the enabled library calls in widget order."""
        if self.fill_nans:
            yield processing.fill_missing_heights, {"radius": self.fill_radius}
        if self.subtract_minimum:
            yield processing.subtract_minimum_height, {}
        if self.transpose:
            yield processing.transpose_surface, {}
        if self.flip_x:
            yield processing.flip_surface, {"axis": "x"}
        if self.flip_y:
            yield processing.flip_surface, {"axis": "y"}
        if self.rotate:
            yield processing.rotate_surface, {"angle_deg": self.angle_deg, "fill_value": 0.0}

    def _update_script(self):
        if not self.file_path.strip():
            self._script.set_code("# Select a metrology file to generate the script.\n")
            return

        path = str(Path(self.file_path).expanduser().absolute())
        lines = [
            "from dabam2d import io, processing, viz",
            "",
            f"surface = io.read_height_profile({path!r}, "
            f"axes_scale={self.axes_scale!r}, height_scale={self.height_scale!r})",
        ]
        for operation, arguments in self._operations():
            call_args = "".join(f", {key}={value!r}" for key, value in arguments.items())
            lines.append(f"surface = processing.{operation.__name__}(surface{call_args})")
        if self.output_path.strip():
            output = str(self._output_file().absolute())
            lines.append(f"io.write_height_profile({output!r}, surface, overwrite=True)")
        lines.extend(("", "viz.plot_height_profile(surface, aspect_ratio=False)", "viz.show()"))
        self._script.set_code("\n".join(lines) + "\n")

    def load_surface(self):
        self._load_surface()
        self._tabs.setCurrentWidget(self._image_tab)

    def _load_surface(self):
        self._input_changed()
        try:
            if not self.file_path.strip():
                raise ValueError("Select a metrology file first.")
            self._loaded_surface = io.read_height_profile(
                Path(self.file_path).expanduser(),
                axes_scale=self.axes_scale,
                height_scale=self.height_scale,
            )
        except Exception as error:
            self._show_error(error)
        else:
            self._adjustments_changed()

    def _current_surface(self):
        if self._loaded_surface is None:
            raise ValueError("Load a surface first.")
        if self._adjusted_surface is None:
            surface = self._loaded_surface
            for operation, arguments in self._operations():
                surface = operation(surface, **arguments)
            self._adjusted_surface = surface

        z = self._adjusted_surface["z"]
        ny, nx = z.shape
        self._summary.setText(f"{nx} × {ny} samples · {numpy.isnan(z).sum()} NaNs")
        return self._adjusted_surface

    def render_surface(self):
        try:
            surface = self._current_surface()
            x, y, z = (surface[key] for key in ("x", "y", "z"))
            dialog = QDialog(self)
            dialog.setAttribute(Qt.WA_DeleteOnClose)
            dialog.setWindowTitle("Surface Preview")
            dialog.resize(740, 580)
            layout = QVBoxLayout(dialog)
            figure = Figure(figsize=(7, 5), layout="constrained")
            axis = figure.add_subplot(projection="3d")
            canvas = FigureCanvas3D(fig=figure, ax=axis, show_legend=False, show_buttons=False)
            xx, yy = numpy.meshgrid(x, y, copy=False)
            if min(z.shape) > 1:
                axis.plot_surface(xx, yy, z, cmap="autumn")
            else:
                axis.scatter(xx.ravel(), yy.ravel(), z.ravel())
            axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Height [m]")
            layout.addWidget(canvas)
            buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
            buttons.rejected.connect(dialog.close)
            layout.addWidget(buttons)
            dialog.show()
        except Exception as error:
            self._show_error(error)

    def _draw_image(self, surface):
        x, y, z = (surface[key] for key in ("x", "y", "z"))
        # A silx image has a constant pitch on each axis. Keep the native
        # scatter view for surfaces with nonuniform or singleton axes.
        if _regular_image_axis(x) and _regular_image_axis(y):
            dx = (x[-1] - x[0]) / (x.size - 1)
            dy = (y[-1] - y[0]) / (y.size - 1)
            self._image.addImage(
                z, origin=(x[0] - dx / 2, y[0] - dy / 2), scale=(dx, dy),
                legend="Height",
            )
        else:
            xx, yy = numpy.meshgrid(x, y, copy=False)
            self._image.addScatter(xx.ravel(), yy.ravel(), z.ravel(), legend="Height")
        self._image.setGraphXLabel("X [m]")
        self._image.setGraphYLabel("Y [m]")
        self._image.setGraphTitle("Height [m]")
        self._image.resetZoom()

    def _select_output(self):
        start = self.output_path
        if not start.strip() and self.file_path.strip():
            source = Path(self.file_path).expanduser()
            start = str(source.with_name(f"{source.stem}_dabam2d.h5"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save as DABAM2D", start, "HDF5 Files (*.h5 *.hdf5)",
            options=QFileDialog.DontConfirmOverwrite,
        )
        if path:
            self.output_path = path
            self.output_path = str(self._output_file())
            self._update_script()

    def save_surface(self):
        try:
            surface = self._current_surface()
            if not self.output_path.strip():
                self._select_output()
                if not self.output_path.strip():
                    return

            destination = self._output_file()
            self.output_path = str(destination)
            self._update_script()
            try:
                io.write_height_profile(destination, surface)
            except FileExistsError:
                answer = QMessageBox.question(
                    self, "Replace file?", f"Replace {destination}?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                io.write_height_profile(destination, surface, overwrite=True)
            self.setStatusMessage(f"Saved {destination}")
        except Exception as error:
            self._show_error(error)

    def _output_file(self):
        path = Path(self.output_path).expanduser()
        return path if path.suffix else path.with_suffix(".h5")

    def _show_error(self, error):
        QMessageBox.critical(self, "DABAM2D", str(error))
        if self.IS_DEVELOP:
            raise error


def _regular_image_axis(axis):
    return axis.size > 1 and numpy.allclose(
        numpy.diff(axis), (axis[-1] - axis[0]) / (axis.size - 1), rtol=1e-4, atol=0,
    )


add_widget_parameters_to_module(__name__)
