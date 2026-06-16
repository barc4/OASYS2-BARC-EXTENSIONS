from AnyQt.QtWidgets import QWidget, QVBoxLayout
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from orangewidget import gui
from orangewidget.settings import Setting
from orangewidget.widget import Input

from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui
from oasys2.widget.gui import MessageDialog, Styles
from oasys2.widget.widget import OWWidget

from barc4beams import Beam
from barc4beams.viz import plot_beam, plot_divergence, plot_phase_space


class OWBeamPlot(OWWidget):
    name = "Beam Plot"
    description = "Plot a barc4beams Beam"
    icon = "icons/barc.png"
    priority = 2
    keywords = ["barc", "barc4beams", "beam", "plot", "divergence", "phase space"]

    want_main_area = 1

    class Inputs:
        beam = Input("BARC Beam", Beam, default=True, auto_summary=False)

    plot_type = Setting(0)
    phase_direction = Setting(2)
    mode = Setting(0)
    aspect_ratio = Setting(True)
    color = Setting(1)
    use_x_range = Setting(False)
    x_range_min = Setting(0.0)
    x_range_max = Setting(0.0)
    use_y_range = Setting(False)
    y_range_min = Setting(0.0)
    y_range_max = Setting(0.0)
    bins = Setting(0)
    z_offset = Setting(0.0)

    MAX_SCATTER_RAYS = 20000

    def __init__(self):
        super().__init__()

        self._beam = None
        self._canvases = []
        self._figures = []

        button_box = oasysgui.widgetBox(
            self.controlArea,
            "",
            addSpace=False,
            orientation="horizontal",
            width=390,
        )
        button = gui.button(button_box, self, "Plot Beam", callback=self.plot_results)
        button.setStyleSheet(Styles.button_blue)

        settings_box = oasysgui.widgetBox(
            self.controlArea,
            "Plot",
            addSpace=True,
            orientation="vertical",
            width=390,
        )

        gui.comboBox(
            settings_box,
            self,
            "plot_type",
            label="Plot",
            labelWidth=160,
            items=["Beam", "Divergence", "Phase Space"],
            sendSelectedValue=False,
            orientation="horizontal",
            callback=self._update_visibility,
        )

        self.phase_direction_box = oasysgui.widgetBox(
            settings_box,
            "",
            addSpace=False,
            orientation="vertical",
        )
        gui.comboBox(
            self.phase_direction_box,
            self,
            "phase_direction",
            label="Direction",
            labelWidth=160,
            items=["X", "Y", "Both"],
            sendSelectedValue=False,
            orientation="horizontal",
        )

        gui.comboBox(
            settings_box,
            self,
            "mode",
            label="Mode",
            labelWidth=160,
            items=["scatter", "hist2d"],
            sendSelectedValue=False,
            orientation="horizontal",
        )
        gui.checkBox(settings_box, self, "aspect_ratio", "Aspect ratio")
        oasysgui.lineEdit(
            settings_box,
            self,
            "color",
            "Color",
            labelWidth=160,
            valueType=int,
            orientation="horizontal",
        )
        oasysgui.lineEdit(
            settings_box,
            self,
            "bins",
            "Bins (0 = auto)",
            labelWidth=160,
            valueType=int,
            orientation="horizontal",
        )
        oasysgui.lineEdit(
            settings_box,
            self,
            "z_offset",
            "Z offset [m]",
            labelWidth=160,
            valueType=float,
            orientation="horizontal",
        )

        range_box = oasysgui.widgetBox(
            self.controlArea,
            "Ranges",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        gui.checkBox(range_box, self, "use_x_range", "Set X range", callback=self._update_visibility)
        self.x_range_box = oasysgui.widgetBox(range_box, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(
            self.x_range_box,
            self,
            "x_range_min",
            "X min",
            labelWidth=160,
            valueType=float,
            orientation="horizontal",
        )
        oasysgui.lineEdit(
            self.x_range_box,
            self,
            "x_range_max",
            "X max",
            labelWidth=160,
            valueType=float,
            orientation="horizontal",
        )

        gui.checkBox(range_box, self, "use_y_range", "Set Y range", callback=self._update_visibility)
        self.y_range_box = oasysgui.widgetBox(range_box, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(
            self.y_range_box,
            self,
            "y_range_min",
            "Y min",
            labelWidth=160,
            valueType=float,
            orientation="horizontal",
        )
        oasysgui.lineEdit(
            self.y_range_box,
            self,
            "y_range_max",
            "Y max",
            labelWidth=160,
            valueType=float,
            orientation="horizontal",
        )

        self.plot_tabs = oasysgui.tabWidget(self.mainArea)

        gui.rubber(self.controlArea)
        self._update_visibility()

    @Inputs.beam
    def set_beam(self, beam):
        self._beam = beam

        if beam is not None:
            self.plot_results()

    def plot_results(self):
        self.setStatusMessage("")

        try:
            if self._beam is None:
                raise ValueError("No BARC Beam input received.")

            mode = self._plot_mode()
            if mode == "scatter" and self._good_rays_count(self._beam) > self.MAX_SCATTER_RAYS:
                MessageDialog.message(
                    parent=self,
                    title="Large Scatter Plot",
                    type="warning",
                    message=(
                        "More than 20000 good rays are available. "
                        "Scatter mode is too heavy for the GUI; defaulting to hist2d."
                    ),
                )
                mode = "hist2d"
                self.mode = 1

            self._clear_plots()

            common_kwargs = {
                "mode": mode,
                "aspect_ratio": bool(self.aspect_ratio),
                "color": int(self.color),
                "x_range": self._range_or_none(self.use_x_range, self.x_range_min, self.x_range_max),
                "y_range": self._range_or_none(self.use_y_range, self.y_range_min, self.y_range_max),
                "bins": self._bins_or_none(),
                "z_offset": float(self.z_offset),
                "plot": False,
            }

            df = self._beam.df

            if self.plot_type == 0:
                fig, _ = plot_beam(df, **common_kwargs)
                self._add_figure_tab("Beam", fig)
            elif self.plot_type == 1:
                fig, _ = plot_divergence(df, **common_kwargs)
                self._add_figure_tab("Divergence", fig)
            else:
                direction = self._phase_direction()
                result = plot_phase_space(df, direction=direction, **common_kwargs)
                if direction == "both":
                    (fig_x, _), (fig_y, _) = result
                    self._add_figure_tab("Phase Space X", fig_x)
                    self._add_figure_tab("Phase Space Y", fig_y)
                else:
                    fig, _ = result
                    self._add_figure_tab(f"Phase Space {direction.upper()}", fig)

            self.setStatusMessage("Plot updated.")
        except Exception as exception:
            self.setStatusMessage(str(exception))
            MessageDialog.message(
                parent=self,
                title="Plot Error",
                type="critical",
                message=str(exception),
            )

    def _add_figure_tab(self, title, figure):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, tab)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        self.plot_tabs.addTab(tab, title)
        self._canvases.append(canvas)
        self._figures.append(figure)
        canvas.draw()

    def _clear_plots(self):
        for figure in self._figures:
            plt.close(figure)

        self._canvases = []
        self._figures = []

        while self.plot_tabs.count() > 0:
            widget = self.plot_tabs.widget(0)
            self.plot_tabs.removeTab(0)
            widget.deleteLater()

    def _update_visibility(self):
        self.phase_direction_box.setVisible(self.plot_type == 2)
        self.x_range_box.setVisible(bool(self.use_x_range))
        self.y_range_box.setVisible(bool(self.use_y_range))

    def _plot_mode(self):
        return "scatter" if self.mode == 0 else "hist2d"

    def _phase_direction(self):
        return ["x", "y", "both"][self.phase_direction]

    def _bins_or_none(self):
        bins = int(self.bins)
        return None if bins <= 0 else bins

    @staticmethod
    def _range_or_none(enabled, minimum, maximum):
        if not enabled:
            return None

        if minimum >= maximum:
            raise ValueError("Range minimum must be smaller than range maximum.")

        return (float(minimum), float(maximum))

    @staticmethod
    def _good_rays_count(beam):
        df = beam.df

        if "lost_ray_flag" not in df.columns:
            return len(df)

        return int((df["lost_ray_flag"] == 0).sum())


add_widget_parameters_to_module(__name__)
