from orangewidget import gui
from orangewidget.widget import OWWidget
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui


class OWBARCPlaceholder(OWWidget):
    name = "BARC Placeholder"
    description = "Placeholder for future BARC Shadow4 widgets"
    icon = "icons/barc.png"
    priority = 1
    keywords = ["barc", "shadow4"]

    want_main_area = 0

    def __init__(self):
        super().__init__()

        box = oasysgui.widgetBox(
            self.controlArea,
            "BARC Shadow4",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        gui.label(
            box,
            self,
            "Placeholder widget for initial package discovery.",
        )
        gui.label(
            box,
            self,
            "Replace this with barc4beams/barc4shadow integration.",
        )
        gui.rubber(self.controlArea)


add_widget_parameters_to_module(__name__)
