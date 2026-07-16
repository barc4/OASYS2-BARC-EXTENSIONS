import contextlib
import io

from orangewidget import gui
from orangewidget.widget import Input

from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui
from oasys2.widget.gui import Styles
from oasys2.widget.widget import OWWidget

from orangecontrib.srw.util.srw_objects import SRWData


class OWWavefrontInfo(OWWidget):
    name = "Wavefront Info"
    description = "Print SRW wavefront mesh statistics"
    icon = "icons/information.png"
    priority = 1
    keywords = ["barc", "srw", "wavefront", "statistics", "info"]

    want_main_area = 1

    class Inputs:
        srw_data = Input("SRW Data", SRWData, default=True, auto_summary=False)

    def __init__(self):
        super().__init__()

        self._srw_data = None

        button_box = oasysgui.widgetBox(
            self.controlArea,
            "",
            addSpace=False,
            orientation="horizontal",
            width=390,
        )
        button = gui.button(button_box, self, "Compute Wavefront Info", callback=self.compute_wavefront_info)
        button.setStyleSheet(Styles.button_blue)

        info_box = oasysgui.widgetBox(
            self.controlArea,
            "Input",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        gui.label(info_box, self, "Accepts SRW Data and prints wavefront mesh statistics.")

        self.stats_output = oasysgui.textArea(height=560, width=760)
        self.stats_output.setStyleSheet("background-color: white; font-family: Courier, monospace;")

        output_box = gui.widgetBox(
            self.mainArea,
            "Wavefront statistics",
            addSpace=True,
            orientation="horizontal",
        )
        output_box.layout().addWidget(self.stats_output)

        gui.rubber(self.controlArea)

    @Inputs.srw_data
    def set_srw_data(self, srw_data):
        self._srw_data = srw_data

        if srw_data is not None:
            self.compute_wavefront_info()

    def compute_wavefront_info(self):
        self.setStatusMessage("")

        try:
            if self._srw_data is None:
                raise ValueError("No SRW Data input received.")

            wavefront = self._srw_data.get_srw_wavefront()
            if wavefront is None:
                raise ValueError("SRW Data does not contain a wavefront.")

            stats_text = format_wavefront_stats(wavefront)
            self.stats_output.setText(stats_text)
            print(stats_text)

            self.setStatusMessage("Wavefront statistics computed.")
        except Exception as exception:
            self.stats_output.setText(str(exception))
            self.setStatusMessage(str(exception))


def format_wavefront_stats(wavefront):
    stream = io.StringIO()

    with contextlib.redirect_stdout(stream):
        wavefront_stats(wavefront)

    return stream.getvalue().strip()


def wavefront_stats(wavefront):
    nx, ny = wavefront.mesh.nx, wavefront.mesh.ny
    range_x = wavefront.mesh.xFin - wavefront.mesh.xStart
    range_y = wavefront.mesh.yFin - wavefront.mesh.yStart
    dx = range_x / (wavefront.mesh.nx - 1)
    dy = range_y / (wavefront.mesh.ny - 1)

    print("\n >>> wavefront parameters:")
    print(f"\tNx = {nx}, Ny = {ny}")
    print(f"\tdx = {dx * 1e6:.3f} \u00b5m, dy = {dy * 1e6:.3f} \u00b5m")
    if range_x >= 0.7e-3 or range_y >= 0.7e-3:
        print(f"\trange x = {range_x * 1e3:.3f} mm, range y = {range_y * 1e3:.3f} mm")
    else:
        print(f"\trange x = {range_x * 1e6:.3f} \u00b5m, range y = {range_y * 1e6:.3f} \u00b5m")

    print(f"\tRx = {wavefront.Rx:.6e} m, Ry = {wavefront.Ry:.6e} m\n")


add_widget_parameters_to_module(__name__)
