from copy import deepcopy
import contextlib
import io
import os
import time

import joblib
from joblib import Parallel, delayed
from orangewidget import gui
from orangewidget.settings import Setting
from orangewidget.widget import Input, Output

from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from oasys2.widget import gui as oasysgui
from oasys2.widget.gui import MessageDialog, Styles
from oasys2.widget.widget import OWWidget

from orangecontrib.barc.shadow4.util.parallel import (
    concatenate_shadow_data,
    cpu_info_text,
    load_runner_module,
    make_runner_module_from_s4beamline,
    print_cpu_info,
    seed_for_iteration,
)
from orangecontrib.shadow4.util.shadow4_objects import ShadowData


class OWParallel(OWWidget):
    name = "Parallel"
    description = "Run additional Shadow4 beamline repetitions in parallel"
    icon = "icons/processing.png"
    priority = 6
    keywords = ["barc", "shadow4", "parallel", "joblib", "repetitions", "seed"]

    want_main_area = 1

    class Inputs:
        shadow_data = Input("Shadow Data", ShadowData, default=True, auto_summary=False)

    class Outputs:
        shadow_data = Output("Shadow Data", ShadowData, default=True, auto_summary=False)

    total_repetitions = Setting(5)
    n_jobs = Setting(-1)
    runner_script_file_name = Setting("parallel_runner_from_oasys.py")

    def __init__(self):
        super().__init__()

        self._shadow_data = None

        button_box = oasysgui.widgetBox(
            self.controlArea,
            "",
            addSpace=False,
            orientation="horizontal",
            width=390,
        )
        button = gui.button(button_box, self, "Run Parallel", callback=self.run_parallel)
        button.setStyleSheet(Styles.button_blue)

        settings_box = oasysgui.widgetBox(
            self.controlArea,
            "Parallel Run",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        oasysgui.lineEdit(
            settings_box,
            self,
            "total_repetitions",
            "Total repetitions",
            labelWidth=190,
            valueType=int,
            orientation="horizontal",
        )
        oasysgui.lineEdit(
            settings_box,
            self,
            "n_jobs",
            "Number of cores",
            labelWidth=190,
            valueType=int,
            orientation="horizontal",
        )

        file_box = oasysgui.widgetBox(
            self.controlArea,
            "Runner Script",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        figure_box = oasysgui.widgetBox(
            file_box,
            "",
            addSpace=True,
            orientation="horizontal",
            width=370,
            height=35,
        )
        self.le_runner_script_file_name = oasysgui.lineEdit(
            figure_box,
            self,
            "runner_script_file_name",
            "Script file",
            labelWidth=90,
            valueType=str,
            orientation="horizontal",
        )
        self.le_runner_script_file_name.setFixedWidth(240)
        gui.button(figure_box, self, "...", callback=self.select_runner_script_file)

        info_box = oasysgui.widgetBox(
            self.controlArea,
            "Input",
            addSpace=True,
            orientation="vertical",
            width=390,
        )
        gui.label(info_box, self, "Total repetitions includes the incoming 0th beam.")
        gui.label(info_box, self, "Parallel jobs = total repetitions - 1.")

        self.run_output = oasysgui.textArea(height=560, width=760)
        output_box = gui.widgetBox(
            self.mainArea,
            "Parallel run log",
            addSpace=True,
            orientation="horizontal",
        )
        output_box.layout().addWidget(self.run_output)

        gui.rubber(self.controlArea)

    @Inputs.shadow_data
    def set_shadow_data(self, shadow_data):
        self._shadow_data = shadow_data

    def select_runner_script_file(self):
        self.le_runner_script_file_name.setText(
            oasysgui.selectSaveFileFromDialog(
                self,
                self.runner_script_file_name,
                default_file_name="parallel_runner_from_oasys.py",
                file_extension_filter="Python Files (*.py)",
            )
        )

    def run_parallel(self):
        self.setStatusMessage("")
        self.Outputs.shadow_data.send(None)
        self.run_output.setText("")

        stream = io.StringIO()
        progress_started = False

        try:
            self._validate_input()
            total_repetitions = self._validate_total_repetitions()
            n_jobs = self._validate_n_jobs()
            n_parallel_runs = total_repetitions - 1

            self.progressBarInit()
            progress_started = True

            with contextlib.redirect_stdout(stream):
                output_data = self._run(total_repetitions, n_parallel_runs, n_jobs)

            log = stream.getvalue().strip()
            self.run_output.setText(log)
            print(log)

            self.Outputs.shadow_data.send(output_data)
            self.setStatusMessage("Accumulated Shadow Data emitted.")
        except Exception as exception:
            self.run_output.setText(str(exception))
            self.setStatusMessage(str(exception))
            MessageDialog.message(
                parent=self,
                title="Parallel Run Error",
                type="critical",
                message=str(exception),
            )
        finally:
            if progress_started:
                self.progressBarFinished()

    def _run(self, total_repetitions, n_parallel_runs, n_jobs):
        t_total = time.perf_counter()

        print_cpu_info()
        print("")
        print("Total repetitions:", total_repetitions)
        print("Parallel repetitions:", n_parallel_runs)
        if n_jobs == -1:
            n_jobs = joblib.cpu_count()
        print("Number of cores:", n_jobs)

        beamline = deepcopy(self._shadow_data.beamline)
        beam = deepcopy(self._shadow_data.beam)
        footprint = deepcopy(self._shadow_data.footprint)

        runner_path = make_runner_module_from_s4beamline(
            beamline,
            module_path=self._runner_script_path(),
        )
        runner_module = load_runner_module(runner_path)
        print("")
        print("Runner module:", runner_path)
        print("")

        base_seed = int(beamline.get_light_source().get_seed())
        seed_list = [seed_for_iteration(base_seed, i) for i in range(n_parallel_runs)]

        self.progressBarSet(10)
        t_parallel = time.perf_counter()
        results = Parallel(n_jobs=n_jobs, backend="loky")(
            delayed(runner_module.run_beamline)(seed)
            for seed in seed_list
        )
        parallel_elapsed = time.perf_counter() - t_parallel
        self.progressBarSet(70)

        seed_list = [result[0] for result in results]
        beam_list = [result[1] for result in results]
        footprint_list = [result[2] for result in results]

        t_concatenate = time.perf_counter()
        beamline_acc, beam_acc, footprint_acc = concatenate_shadow_data(
            beamline,
            beam,
            beam_list,
            footprint,
            footprint_list,
            seed_list,
            verbose=True,
        )
        concatenate_elapsed = time.perf_counter() - t_concatenate
        self.progressBarSet(95)

        output_data = ShadowData(
            beam=beam_acc,
            footprint=footprint_acc,
            number_of_rays=beam_acc.N,
            beamline=beamline_acc,
        )
        output_data.initial_flux = self._shadow_data.initial_flux
        output_data.scanning_data = self._shadow_data.scanning_data

        print("")
        print("Parallel elapsed: %.3f s" % parallel_elapsed)
        print("Concatenation elapsed: %.3f s" % concatenate_elapsed)
        print("Total elapsed: %.3f s" % (time.perf_counter() - t_total))
        print("Accumulated rays:", beam_acc.N)
        # print(beamline_acc.get_light_source().get_info())

        self.progressBarSet(100)
        return output_data

    def _validate_input(self):
        if self._shadow_data is None:
            raise ValueError("No Shadow Data input received.")
        if self._shadow_data.beam is None:
            raise ValueError("Shadow Data does not contain a beam.")
        if self._shadow_data.beamline is None:
            raise ValueError("Shadow Data does not contain an S4 beamline.")
        if self._shadow_data.beamline.get_light_source() is None:
            raise ValueError("Shadow Data beamline does not contain a light source.")
        if not str(self.runner_script_file_name).strip():
            raise ValueError("Runner script file name is empty.")

    def _validate_total_repetitions(self):
        total_repetitions = int(self.total_repetitions)

        if total_repetitions < 1:
            raise ValueError("Total repetitions must be at least 1.")

        self.total_repetitions = total_repetitions
        return total_repetitions

    def _validate_n_jobs(self):
        n_jobs = int(self.n_jobs)
        cpu_count = joblib.cpu_count()

        if n_jobs == 0:
            self.n_jobs = -1
            MessageDialog.message(
                parent=self,
                title="Invalid Core Count",
                type="warning",
                message="Number of cores cannot be 0. Using -1 instead.",
            )
            return -1

        if n_jobs > cpu_count:
            self.n_jobs = -1
            MessageDialog.message(
                parent=self,
                title="Invalid Core Count",
                type="warning",
                message=(
                    "Requested %d cores, but joblib reports %d available. "
                    "Using -1 instead.\n\n%s"
                )
                % (n_jobs, cpu_count, cpu_info_text()),
            )
            return -1

        self.n_jobs = n_jobs
        return n_jobs

    def _runner_script_path(self):
        file_name = str(self.runner_script_file_name).strip()

        if not file_name.endswith(".py"):
            file_name += ".py"
            self.runner_script_file_name = file_name
            self.le_runner_script_file_name.setText(file_name)

        if os.path.isabs(file_name):
            return file_name

        return os.path.abspath(file_name)


add_widget_parameters_to_module(__name__)
