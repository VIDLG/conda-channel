"""Smoke test for package-pin APIs, executed by nextpnr's ``--run`` option."""

from typing import Protocol, cast


class PackagePinContext(Protocol):
    def getPackagePins(self) -> list[str]: ...

    def getPackagePinBel(self, pin: str) -> str: ...

    def getBelPackagePin(self, bel: str) -> str: ...


context = cast(PackagePinContext, globals()["ctx"])
package_pins = context.getPackagePins()
assert isinstance(package_pins, list)
assert package_pins
assert all(isinstance(pin, str) and pin for pin in package_pins)
assert len(package_pins) == len(set(package_pins))

for pin in package_pins:
    bel = context.getPackagePinBel(pin)
    assert isinstance(bel, str) and bel
    assert context.getBelPackagePin(bel) == pin

assert context.getPackagePinBel("__nextpnr_unknown_package_pin__") == ""
print(f"package-pin smoke test passed: {len(package_pins)} package pins")
