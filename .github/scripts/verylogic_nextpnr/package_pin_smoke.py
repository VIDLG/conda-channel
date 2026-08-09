"""Smoke test for package-pin APIs, executed by nextpnr's ``--run`` option."""

from collections.abc import Iterable
from typing import Protocol, cast


class DelayBounds(Protocol):
    def minDelay(self) -> int | float: ...

    def maxDelay(self) -> int | float: ...


class PackagePinContext(Protocol):
    def archId(self) -> str: ...

    def getChipName(self) -> str: ...

    def getDeviceName(self) -> str: ...

    def getPackageName(self) -> str | None: ...

    def getUArchName(self) -> str | None: ...

    def getTargetIdentity(self) -> dict[str, str | None]: ...

    def getCapabilities(self) -> dict[str, bool]: ...

    def getWires(self) -> Iterable[str]: ...

    def getWireDelay(self, wire: str) -> DelayBounds | None: ...

    def getPackagePins(self) -> list[str]: ...

    def getPackagePinBel(self, pin: str) -> str | None: ...

    def getBelPackagePin(self, bel: str) -> str | None: ...


EXPECTED_TARGETS = {
    ("ice40", "lp384"): ("qn32", None),
    ("ice40", "lp1k"): ("tq144", None),
    ("ice40", "lp4k"): ("tq144", None),
    ("ice40", "lp8k"): ("ct256", None),
    ("ice40", "hx1k"): ("tq144", None),
    ("ice40", "hx4k"): ("tq144", None),
    ("ice40", "hx8k"): ("ct256", None),
    ("ice40", "up3k"): ("sg48", None),
    ("ice40", "up5k"): ("sg48", None),
    ("ice40", "u1k"): ("sg48", None),
    ("ice40", "u2k"): ("sg48", None),
    ("ice40", "u4k"): ("sg48", None),
    ("himbaechel", "GW1N-LV1QN48C6/I5"): ("GW1N-LV1QN48", "gowin"),
    ("himbaechel", "GW1NZ-LV1CG25C5/I4"): ("GW1NZ-LV1CG25", "gowin"),
    ("himbaechel", "GW1N-LV4CS72C5/I4"): ("GW1N-LV4CS72", "gowin"),
    ("himbaechel", "GW1N-LV9CM64C6/I5"): ("GW1N-LV9CM64", "gowin"),
    ("himbaechel", "GW1N-LV9CM64C7/I6"): ("GW1N-LV9CM64", "gowin"),
    ("himbaechel", "GW1NSR-LV4CMG64PC6/I5"): ("GW1NSR-LV4CMG64P", "gowin"),
    ("himbaechel", "GW2A-LV18EQ144C7/I6"): ("GW2A-LV18EQ144", "gowin"),
    ("himbaechel", "GW2AR-LV18EQ176C8/I7"): ("GW2AR-LV18EQ176", "gowin"),
    ("himbaechel", "GW5A-LV25LQ100C1/I0"): ("GW5A-LV25LQ100", "gowin"),
    ("himbaechel", "GW5AST-LV138FPG676AC1/I0"): ("GW5AST-LV138FPG676A", "gowin"),
    ("himbaechel", "xc7a100tcsg324-1"): ("csg324", "xilinx"),
}


context = cast(PackagePinContext, globals()["ctx"])
architecture = context.archId()
device = context.getDeviceName()
package = context.getPackageName()
uarch = context.getUArchName()
assert (architecture, device) in EXPECTED_TARGETS
assert (package, uarch) == EXPECTED_TARGETS[(architecture, device)]
chip = context.getChipName()
assert isinstance(chip, str) and chip
assert context.getTargetIdentity() == {
    "architecture": architecture,
    "device": device,
    "chip": chip,
    "package": package,
    "uarch": uarch,
}
assert not hasattr(context, "getActualRouteDelay")

capabilities = context.getCapabilities()
assert isinstance(capabilities, dict)
assert capabilities["wire_delay"] is (architecture == "ice40")
wire_delay = context.getWireDelay(next(iter(context.getWires())))
if capabilities["wire_delay"]:
    assert wire_delay is not None
    assert wire_delay.minDelay() <= wire_delay.maxDelay()
else:
    assert wire_delay is None

package_pins = context.getPackagePins()
assert isinstance(package_pins, list)
assert package_pins
assert all(isinstance(pin, str) and pin for pin in package_pins)
assert len(package_pins) == len(set(package_pins))

bonded_io_pins = 0
for pin in package_pins:
    bel = context.getPackagePinBel(pin)
    if bel is None:
        continue
    assert isinstance(bel, str) and bel
    assert context.getBelPackagePin(bel) == pin
    bonded_io_pins += 1

assert bonded_io_pins > 0
assert context.getPackagePinBel("__nextpnr_unknown_package_pin__") is None
target = f"{architecture}/{device}/{package}"
pin_summary = f"{bonded_io_pins}/{len(package_pins)}"
print(f"target identity and package-pin smoke passed: {target}, uarch={uarch}, bonded={pin_summary}")
