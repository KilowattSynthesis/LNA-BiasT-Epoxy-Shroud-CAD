"""Potting shell for an SPF5189Z LNA board + SMA M-M adapter + bias tee.

Dimensions were traced from a top-down photo against a metric ruler
(scale ~10.35 px/mm). Plan-view (X/Y) numbers are good to roughly +/-0.5 mm.
Heights (Z) are NOT visible in a top-down photo, so they are typical values
for these parts - measure yours with calipers and adjust the Spec.

Coordinate system:
- X: along the RF axis. X=0 is the left (RFin) edge of the green LNA board.
- Y: across the boards. Y=0 is the SMA connector axis. +Y is "up" in the photo
  (towards the GND/VCC pads and the black jumper wires).
- Z: Z=0 is the SMA axis, which is also the mid-plane of both PCBs
  (edge-launch connectors straddle the board).

The shell is an open-top tray with 1 mm walls. The two end SMA connectors exit
through U-slots in the end walls; the assembly drops in from the top and the
connector threads rest in the bottom of the U-slots, self-locating it.
Print two `slot_plug` parts and glue them into the U-slots above the threads
(from the outside) before pouring, so epoxy can't leak out.
"""

from dataclasses import dataclass
from pathlib import Path

import build123d as bd
from build123d_ease import show
from loguru import logger


def box_from_bounds(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> bd.Part:
    """Create a box from min/max coordinates."""
    return bd.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * bd.Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def x_cylinder(x0: float, x1: float, radius: float) -> bd.Part:
    """Create a cylinder along the X axis, centred on the SMA axis."""
    return bd.Pos((x0 + x1) / 2, 0, 0) * (
        bd.Rot(0, 90, 0) * bd.Cylinder(radius=radius, height=x1 - x0)
    )


@dataclass
class Spec:
    """Specification for the potting shell."""

    # ---- Traced from photo (plan view, mm) ----
    # Green SPF5189Z LNA board.
    lna_board_x: tuple[float, float] = (0.0, 34.0)
    lna_board_y: tuple[float, float] = (-11.3, 13.7)

    # Shield can on the LNA board.
    lna_shield_x: tuple[float, float] = (5.5, 27.7)
    lna_shield_y: tuple[float, float] = (-7.0, 9.1)

    # SMA male-male adapter between the boards.
    adapter_x: tuple[float, float] = (34.0, 65.2)

    # Purple bias-tee board.
    tee_board_x: tuple[float, float] = (65.2, 85.0)
    tee_board_y: tuple[float, float] = (-5.4, 10.5)

    # Left SMA (RFin): square flange body, then threaded barrel.
    left_sma_flange_x: tuple[float, float] = (-2.9, 0.0)
    left_sma_thread_x: tuple[float, float] = (-11.3, -2.9)

    # Right SMA (RF+DC): square flange body, then threaded barrel.
    right_sma_flange_x: tuple[float, float] = (85.0, 87.9)
    right_sma_thread_x: tuple[float, float] = (87.9, 95.4)

    # Black jumper wires loop past the LNA board's +Y edge to about here.
    wire_loop_max_y_lna: float = 15.2
    wire_loop_max_y_tee: float = 11.8

    # ---- Typical part dimensions (NOT measurable from photo - check!) ----
    pcb_thickness: float = 1.6
    lna_shield_height: float = 4.5  # Above top of LNA PCB.
    tee_component_height: float = 1.2  # Small SMD parts on the bias tee.
    sma_thread_dia: float = 6.35  # 1/4"-36 UNS.
    sma_flange_size: float = 7.0  # Body behind the thread (~6.5-7 in photo).
    adapter_hex_corner_dia: float = 9.2  # 5/16" hex across corners.
    adapter_mean_dia: float = 8.0  # For epoxy displacement estimate.

    # ---- Shell design parameters ----
    wall: float = 1.0
    clearance_xy: float = 1.5  # Epoxy gap around boards/wires.
    end_wall_gap: float = 0.3  # Gap between SMA flange and end wall.
    floor_gap: float = 1.0  # Epoxy under the lowest part (adapter hex).
    epoxy_cover: float = 1.7  # Epoxy above the tallest part (shield can).
    lip_above_fill: float = 1.0  # Wall height above the fill line.
    slot_clearance: float = 0.25  # Diametral clearance on the SMA thread.
    plug_clearance: float = 0.15  # Per side, plug-to-slot fit.

    # Epoxy density for the mass estimate (typical 1.1-1.2 g/cm^3).
    epoxy_density_g_per_cm3: float = 1.15

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert self.wall > 0
        assert self.lna_board_x[1] <= self.adapter_x[0] + 0.01
        assert self.adapter_x[1] <= self.tee_board_x[0] + 0.01
        # The slot must be narrower than the SMA flange, or the part slides out.
        assert self.slot_width < self.sma_flange_size

    # ---- Derived values ----
    @property
    def slot_width(self) -> float:
        """Width of the U-slot that the SMA threads drop into."""
        return self.sma_thread_dia + self.slot_clearance

    @property
    def floor_top_z(self) -> float:
        """Top surface of the floor (bottom of the epoxy)."""
        return -self.adapter_hex_corner_dia / 2 - self.floor_gap

    @property
    def tallest_part_z(self) -> float:
        """Top of the tallest component (LNA shield can)."""
        return self.pcb_thickness / 2 + self.lna_shield_height

    @property
    def fill_z(self) -> float:
        """Epoxy fill line."""
        return self.tallest_part_z + self.epoxy_cover

    @property
    def wall_top_z(self) -> float:
        """Top of the shell walls."""
        return self.fill_z + self.lip_above_fill

    @property
    def inner_x_min(self) -> float:
        """Inner face of the left end wall."""
        return self.left_sma_flange_x[0] - self.end_wall_gap

    @property
    def inner_x_max(self) -> float:
        """Inner face of the right end wall."""
        return self.right_sma_flange_x[1] + self.end_wall_gap

    @property
    def lna_section_y(self) -> tuple[float, float]:
        """Inner Y extent of the wide section around the LNA board."""
        return (
            self.lna_board_y[0] - self.clearance_xy,
            max(self.lna_board_y[1], self.wire_loop_max_y_lna)
            + self.clearance_xy,
        )

    @property
    def tee_section_y(self) -> tuple[float, float]:
        """Inner Y extent of the narrow section (adapter + bias tee)."""
        return (
            min(self.tee_board_y[0], -self.adapter_hex_corner_dia / 2)
            - self.clearance_xy,
            max(self.tee_board_y[1], self.wire_loop_max_y_tee)
            + self.clearance_xy,
        )

    @property
    def lna_section_x_max(self) -> float:
        """Where the wide LNA section steps down to the narrow section."""
        return self.lna_board_x[1] + self.clearance_xy


def cavity(spec: Spec, z_top: float) -> bd.Part:
    """Inner volume of the shell, from the floor up to `z_top`."""
    z0 = spec.floor_top_z
    p = bd.Part(None)
    p += box_from_bounds(
        spec.inner_x_min,
        spec.lna_section_x_max,
        *spec.lna_section_y,
        z0,
        z_top,
    )
    p += box_from_bounds(
        spec.lna_section_x_max - 0.01,  # Small overlap for a clean union.
        spec.inner_x_max,
        *spec.tee_section_y,
        z0,
        z_top,
    )
    return p


def device_envelope(spec: Spec) -> bd.Part:
    """Approximate solid model of the traced assembly (for displacement)."""
    t = spec.pcb_thickness
    p = bd.Part(None)

    # PCBs.
    p += box_from_bounds(*spec.lna_board_x, *spec.lna_board_y, -t / 2, t / 2)
    p += box_from_bounds(*spec.tee_board_x, *spec.tee_board_y, -t / 2, t / 2)

    # Shield can and bias-tee components.
    p += box_from_bounds(
        *spec.lna_shield_x,
        *spec.lna_shield_y,
        t / 2,
        t / 2 + spec.lna_shield_height,
    )
    p += box_from_bounds(
        spec.tee_board_x[0] + 3,
        spec.tee_board_x[1] - 3,
        -3,
        8,
        t / 2,
        t / 2 + spec.tee_component_height,
    )

    # Adapter.
    p += x_cylinder(*spec.adapter_x, spec.adapter_mean_dia / 2)

    # End SMA connectors.
    f = spec.sma_flange_size / 2
    for flange_x, thread_x in (
        (spec.left_sma_flange_x, spec.left_sma_thread_x),
        (spec.right_sma_flange_x, spec.right_sma_thread_x),
    ):
        p += box_from_bounds(*flange_x, -f, f, -f, f)
        p += x_cylinder(*thread_x, spec.sma_thread_dia / 2)

    return p


def slot_cutter(spec: Spec, x0: float, x1: float, width: float) -> bd.Part:
    """U-shaped cutter: half-cylinder at the SMA axis, open to the top."""
    p = bd.Part(None)
    p += x_cylinder(x0, x1, width / 2)
    p += box_from_bounds(x0, x1, -width / 2, width / 2, 0, spec.wall_top_z + 5)
    return p


def potting_shell(spec: Spec) -> bd.Part | bd.Compound:
    """Create the open-top 1 mm potting shell."""
    w = spec.wall
    p = bd.Part(None)

    # Outer: the cavity grown by the wall thickness on every side but the top.
    lna_y = spec.lna_section_y
    tee_y = spec.tee_section_y
    z0 = spec.floor_top_z - w
    p += box_from_bounds(
        spec.inner_x_min - w,
        spec.lna_section_x_max + w,
        lna_y[0] - w,
        lna_y[1] + w,
        z0,
        spec.wall_top_z,
    )
    p += box_from_bounds(
        spec.lna_section_x_max,
        spec.inner_x_max + w,
        tee_y[0] - w,
        tee_y[1] + w,
        z0,
        spec.wall_top_z,
    )

    # Hollow it out (cavity runs past the top, so the tray is open).
    p -= cavity(spec, spec.wall_top_z + 1)

    # U-slots in the end walls for the SMA threads.
    p -= slot_cutter(
        spec, spec.inner_x_min - w - 1, spec.inner_x_min + 1, spec.slot_width
    )
    p -= slot_cutter(
        spec, spec.inner_x_max - 1, spec.inner_x_max + w + 1, spec.slot_width
    )

    return p


def slot_plug(spec: Spec) -> bd.Part | bd.Compound:
    """Plug that fills a U-slot above the SMA thread.

    Made of a tongue that sits in the slot (wall thick) plus a cover plate
    that laps over the outside of the wall. Glue it on from the outside.
    Modelled at the left end wall position; print 2.
    """
    w = spec.wall
    x_wall_out = spec.inner_x_min - w
    x_wall_in = spec.inner_x_min
    tongue_half = spec.slot_width / 2 - spec.plug_clearance
    plate_half = spec.slot_width / 2 + 2.0

    p = bd.Part(None)
    p += box_from_bounds(
        x_wall_out, x_wall_in, -tongue_half, tongue_half, 0, spec.wall_top_z
    )
    p += box_from_bounds(
        x_wall_out - w, x_wall_out, -plate_half, plate_half, 0, spec.wall_top_z
    )
    # Saddle that sits on top of the thread.
    p -= x_cylinder(
        x_wall_out - w - 1, x_wall_in + 1, spec.sma_thread_dia / 2 + 0.1
    )
    return p


def log_epoxy_estimate(spec: Spec) -> None:
    """Log how much potting epoxy the shell will take."""
    fill_volume = cavity(spec, spec.fill_z).volume  # mm^3
    displaced = (device_envelope(spec) & cavity(spec, spec.fill_z)).volume
    epoxy_mm3 = fill_volume - displaced
    epoxy_ml = epoxy_mm3 / 1000
    epoxy_g = epoxy_ml * spec.epoxy_density_g_per_cm3

    logger.info(f"Cavity volume to fill line:   {fill_volume / 1000:6.1f} mL")
    logger.info(f"Displaced by the assembly:    {displaced / 1000:6.1f} mL")
    logger.info(
        f"Epoxy needed (net):           {epoxy_ml:6.1f} mL "
        f"(~{epoxy_g:.0f} g at {spec.epoxy_density_g_per_cm3} g/cm^3)"
    )
    logger.info(
        f"Mix ~{epoxy_ml * 1.2:.0f} mL to allow ~20% for cup/stick losses."
    )
    logger.info(
        f"Fill line is {spec.fill_z - spec.floor_top_z:.1f} mm above the floor "
        f"({spec.epoxy_cover} mm over the shield can)."
    )


if __name__ == "__main__":
    spec = Spec()
    log_epoxy_estimate(spec)

    parts = {
        "potting_shell": show(potting_shell(spec)),
        "slot_plug": show(slot_plug(spec)),
        "device_envelope_reference": (device_envelope(spec)),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
