from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for tube_shroud."""

    shroud_od: float = 33.5
    # 43 OD, 33.8 ID

    sma_hole_d: float = 6.0 + 0.2

    antenna_od: float = 13.0 + 0.2
    antenna_height_axial: float = 6.0 + 2.0

    lna_width: float = 28.0 + 2.0
    lna_length_axial: float = 33.0
    lna_thickness: float = 8.0

    sma_joiner_length_axial: float = 36.0
    sma_joiner_d: float = 13.0

    bias_tee_length_axial: float = 25.0 + 2.0  # Add square connector bit.
    bias_tee_width: float = 15 + 3.0
    bias_tee_thickness: float = 8.0
    bias_tee_shift: float = 2.5
    # Bias tee is 15mm: 5mm on one side and 10mm on the other.

    bottom_wall_thickness: float = 1.8

    enable_go_out_top: bool = False

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert True

    @property
    def shroud_h(self) -> float:
        """Height of the shroud."""
        return (
            self.antenna_height_axial
            + self.lna_length_axial
            + self.sma_joiner_length_axial
            + self.bias_tee_length_axial
            + self.bottom_wall_thickness
        )

    @property
    def go_out_top_num(self) -> int:
        """Arbitrarily large number to force extension to top."""
        return int(self.enable_go_out_top) * 1000


def tube_shroud(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of tube_shroud.

    - Bias Tee on the bottom, then LNA, then antenna on top.
    """
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.shroud_od / 2,
        height=spec.shroud_h,
        align=bde.align.ANCHOR_BOTTOM,
    )

    p -= bd.Cylinder(
        radius=spec.sma_hole_d / 2,
        height=spec.shroud_h,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Starting the from bottom, remove the bias tee volume.
    p -= bd.Pos(
        Z=spec.bottom_wall_thickness,
        X=spec.bias_tee_shift,
    ) * bd.Box(
        spec.bias_tee_width,
        spec.bias_tee_thickness,
        spec.bias_tee_length_axial + spec.go_out_top_num,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the part between the bias tee and the LNA.
    p -= bd.Pos(
        Z=spec.bottom_wall_thickness + spec.bias_tee_length_axial
    ) * bd.Cylinder(
        radius=spec.sma_joiner_d / 2,
        height=spec.sma_joiner_length_axial + spec.go_out_top_num,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the LNA volume.
    p -= bd.Pos(
        Z=spec.bottom_wall_thickness
        + spec.bias_tee_length_axial
        + spec.sma_joiner_length_axial
    ) * bd.Box(
        spec.lna_width,
        spec.lna_thickness,
        spec.lna_length_axial + spec.go_out_top_num,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the antenna volume.
    p -= bd.Pos(
        Z=spec.bottom_wall_thickness
        + spec.bias_tee_length_axial
        + spec.sma_joiner_length_axial
        + spec.lna_length_axial
    ) * bd.Cylinder(
        radius=spec.antenna_od / 2,
        height=spec.antenna_height_axial + spec.go_out_top_num,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # For render, remove half of everything.
    p -= bd.Box(
        spec.shroud_od,
        spec.shroud_h,
        200,
        align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.MIN),
    )

    return p


if __name__ == "__main__":
    parts = {
        "tube_shroud": show(tube_shroud(Spec())),
    }

    logger.info("Showing CAD model(s)")

    (
        export_folder := Path(__file__).parent.with_name("build")
        / Path(__file__).stem
    ).mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
