"""Runtime provenance for DABAM2D widget signals."""

from dataclasses import dataclass, replace

from oasys2.widget.util.widget_objects import OasysSurfaceData


@dataclass(frozen=True)
class Operation:
    name: str
    arguments: tuple[tuple[str, str | int | float], ...]
    result: str = "surface"

    def script_line(self):
        arguments = "".join(f", {key}={value!r}" for key, value in self.arguments)
        return f"{self.result} = processing.{self.name}(surface{arguments})"


@dataclass(frozen=True)
class SurfaceRecipe:
    source_path: str | None
    axes_scale: float = 1.0
    height_scale: float = 1.0
    operations: tuple[Operation, ...] = ()
    output_path: str | None = None
    legacy: bool = False

    def append(self, operation):
        return replace(self, operations=(*self.operations, operation))

    def python_script(self):
        lines = []
        if self.legacy:
            lines.append("# The upstream widget supplied no operation history.")
        if self.source_path is None:
            lines.append("# A standalone replay requires a readable upstream HDF5 file.")
            return "\n".join(lines) + "\n"

        lines.extend(("from dabam2d import io, processing, viz", ""))
        if self.legacy:
            lines.extend((
                "import h5py",
                "",
                f"with h5py.File({self.source_path!r}, 'r') as file:",
                "    group = file['surface_file']",
                "    surface = {key.lower(): group[key][()] for key in ('X', 'Y', 'Z')}",
            ))
        else:
            lines.append(
                f"surface = io.read_height_profile({self.source_path!r}, "
                f"axes_scale={self.axes_scale!r}, height_scale={self.height_scale!r})"
            )
        lines.extend(operation.script_line() for operation in self.operations)
        lines.append("")
        if self.output_path is not None:
            lines.append(f"io.write_height_profile({self.output_path!r}, surface, overwrite=True)")
        lines.append("viz.plot_height_profile(surface, aspect_ratio=False)")
        if self.operations and self.operations[-1].result == "cut":
            lines.append("viz.plot_height_cut(cut)")
        lines.append("viz.show()")
        return "\n".join(lines) + "\n"


class Dabam2DSurfaceData(OasysSurfaceData):
    """OASYS-compatible surface with the widget operations that produced it."""

    def __init__(self, *, recipe, **surface_data):
        super().__init__(**surface_data)
        self.recipe = recipe


@dataclass(frozen=True)
class HeightCutData:
    cut: dict
    recipe: SurfaceRecipe
