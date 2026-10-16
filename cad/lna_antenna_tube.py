from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for tube_shroud."""

    shroud_od: float = 33.5  # Pipe ID.
    pipe_od: float = 42.8
    # 43 OD, 33.8 ID

    sma_hole_d: float = 6.0 + 0.2

    antenna_od: float = 13.0 + 0.2
    antenna_height_axial: float = 6.0 + 2.0

    lna_width: float = 28.0 + 2.0
    lna_length_axial: float = 33.0
    lna_thickness: float = 8.0

    sma_joiner_length_axial: float = 30.7
    sma_joiner_d: float = 13.0

    bias_tee_length_axial: float = 20.0 + 2.0  # Add square connector bit.
    bias_tee_width: float = 15 + 3.0
    bias_tee_thickness: float = 8.0
    bias_tee_shift: float = -2.5
    # Bias tee is 15mm: 5mm on one side and 10mm on the other.

    extra_pcb_length_axial: float = 3.0
    """Extra PCB length to extend into the "SMA joiner" section.

    Extends both the bias tee and LNA.
    """

    bottom_wall_thickness: float = 1.8

    registration_ball_d: float = 0.0

    top_wall_thickness: float = 4.0
    side_wall_thickness: float = 4.0
    side_wall_height: float = 25.0

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

    # Remove the SMA hole volume out the bottom.
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
        (
            spec.bias_tee_length_axial
            + spec.extra_pcb_length_axial
            + spec.go_out_top_num
        ),
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
        - spec.extra_pcb_length_axial
    ) * bd.Box(
        spec.lna_width,
        spec.lna_thickness,
        spec.lna_length_axial
        + spec.extra_pcb_length_axial
        + spec.go_out_top_num,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # For render, remove half of everything.
    p -= bd.Pos(Y=-4) * bd.Box(
        spec.shroud_od,
        spec.shroud_h,
        200,
        align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.MIN),
    )

    # Add the top wall.
    p += bd.Part() + (
        bd.Pos(Z=spec.shroud_h)
        * bd.Cylinder(
            radius=spec.pipe_od / 2 + spec.side_wall_thickness,
            height=spec.top_wall_thickness + spec.side_wall_height,
            align=bde.align.ANCHOR_TOP,
        )
        - bd.Pos(Z=spec.shroud_h - spec.top_wall_thickness)
        * bd.Cylinder(
            radius=spec.pipe_od / 2,
            height=spec.top_wall_thickness + spec.side_wall_height,
            align=bde.align.ANCHOR_TOP,
        )
    )

    # Remove spot for grounding wires.
    for x in [-10, 10]:
        p -= bd.Pos(X=x, Y=-2, Z=spec.shroud_h - 10) * bd.Cylinder(
            radius=1, height=20
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

    # Add a registration ball to the halves.
    if spec.registration_ball_d:
        ball_x_pos = (
            spec.sma_joiner_d / 2
            + (spec.shroud_od / 2 - spec.sma_joiner_d / 2) / 2
        )
        p -= bd.Pos(
            Z=spec.shroud_h / 2,
            X=ball_x_pos,
            Y=0.01,
        ) * bd.Sphere(radius=spec.registration_ball_d / 2)
        p += bd.Pos(
            Z=spec.shroud_h / 2,
            X=-ball_x_pos,
            Y=0.01,
        ) * bd.Sphere(radius=spec.registration_ball_d / 2)

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
