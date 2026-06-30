import re
import shutil
import subprocess

from app.constants import VBOX_CMD, VBOX_IFACE
from app.style import C, clear, line, render_header, step_fail, step_warn
from app.input import ask, confirm, go_back, select
from app.spinner import Spinner
from app.config import get_setting, save_config, set_setting


def _has_command(name: str) -> bool:
    return shutil.which(name) is not None


def detect_radmin_bridge() -> str | None:
    try:
        out = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", VBOX_IFACE],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    m = re.search(r"inet (26\.\d+\.\d+\.\d+)", out.stdout)
    return m.group(1) if m else None


def bridge_present() -> bool:
    try:
        out = subprocess.run([VBOX_CMD, "list", "hostonlyifs"],
                             capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False
    return bool(re.search(rf"\b{VBOX_IFACE}\b", out.stdout))


def competing_route() -> str | None:
    try:
        out = subprocess.run(
            ["ip", "-o", "route", "show"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None
    for route in out.stdout.splitlines():
        m = re.match(r"^26\.\S+\s+.*\bdev\s+(\S+)", route)
        if m and m.group(1) != VBOX_IFACE:
            return m.group(1)
    return None


def _run_quiet(
    cmd: list[str], ok_if: tuple[str, ...] = ()
) -> tuple[str | None, bool]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return f"{cmd[0]}: command not found", False
    if out.returncode == 0:
        return None, False
    err = (out.stderr or out.stdout).strip()
    if any(token in err for token in ok_if):
        return None, True
    detail = err.splitlines()[0] if err else f"exit code {out.returncode}"
    return detail, False


def _run_steps(
    steps: list[tuple[list[str], tuple[str, ...]]],
) -> tuple[str | None, bool]:
    changed = False
    for cmd, ok_if in steps:
        err, already = _run_quiet(cmd, ok_if)
        if err:
            return err, changed
        if ok_if and not already:
            changed = True
    return None, changed


def verify_bridge(radmin_ip: str) -> bool:
    try:
        addr_out = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", "dev", VBOX_IFACE],
            capture_output=True, text=True, check=False,
        ).stdout
        if f"inet {radmin_ip}/8" not in addr_out:
            return False
        route_out = subprocess.run(
            ["ip", "route", "show", "dev", VBOX_IFACE],
            capture_output=True, text=True, check=False,
        ).stdout
    except FileNotFoundError:
        return False
    return (
        "224.0.0.0/4" in route_out
        and "26.255.255.255" in route_out
        and "255.255.255.255" in route_out
    )


def create_bridge(
    radmin_ip: str, elevate: list[str]
) -> tuple[str | None, bool, bool]:
    created = not bridge_present()
    steps: list[tuple[list[str], tuple[str, ...]]] = [
        ([*elevate, "modprobe", "vboxnetadp"], ()),
        ([*elevate, "chmod", "0666", "/dev/vboxnetctl"], ()),
    ]
    if created:
        steps.append(([VBOX_CMD, "hostonlyif", "create"], ()))
    steps += [
        ([VBOX_CMD, "hostonlyif", "ipconfig", VBOX_IFACE,
          "--ip", radmin_ip, "--netmask", "255.0.0.0"], ()),
        ([*elevate, "ip", "link", "set", VBOX_IFACE, "up"], ()),
        ([*elevate, "ip", "addr", "add", f"{radmin_ip}/8", "dev", VBOX_IFACE],
         ("File exists", "already assigned")),
        ([*elevate, "ip", "route", "add", "224.0.0.0/4", "dev", VBOX_IFACE],
         ("File exists",)),
        ([*elevate, "ip", "route", "add", "26.255.255.255/32",
          "dev", VBOX_IFACE],
         ("File exists",)),
        ([*elevate, "ip", "route", "add", "255.255.255.255/32",
          "dev", VBOX_IFACE],
         ("File exists",)),
    ]
    error, changed = _run_steps(steps)
    return error, changed, created


def remove_bridge(elevate: list[str]) -> str | None:
    error, _ = _run_steps([
        ([*elevate, "ip", "addr", "flush", "dev", VBOX_IFACE], ()),
        ([*elevate, "ip", "link", "set", VBOX_IFACE, "down"], ()),
        ([VBOX_CMD, "hostonlyif", "remove", VBOX_IFACE], ()),
    ])
    return error


def list_vms() -> list[str] | None:
    out = subprocess.run(
        [VBOX_CMD, "list", "vms"], capture_output=True, text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    return re.findall(r'"([^"]+)"', out.stdout)


def vm_state(vm_name: str) -> str | None:
    info = subprocess.run(
        [VBOX_CMD, "showvminfo", vm_name, "--machinereadable"],
        capture_output=True, text=True, check=False,
    )
    if info.returncode != 0:
        return None
    state_match = re.search(r'VMState="([^"]+)"', info.stdout)
    return state_match.group(1) if state_match else "unknown"


def attach_vm(vm_name: str) -> str | None:
    rc = subprocess.run(
        [
            VBOX_CMD, "modifyvm", vm_name, "--nic2", "hostonly",
            "--hostonlyadapter2", VBOX_IFACE,
        ],
        capture_output=True, text=True, check=False,
    )
    if rc.returncode != 0:
        err = (rc.stderr or rc.stdout).strip().splitlines()
        return err[0] if err else "unknown error"
    return None


def _radmin_create(cfg: dict) -> None:
    render_header("Create bridge")
    if not _has_command(VBOX_CMD):
        step_fail("Install VirtualBox first")
        go_back()
        return
    if not _has_command("sudo"):
        step_fail("Install sudo first")
        go_back()
        return
    conflict = competing_route()
    if conflict:
        step_fail(
            f"Another interface '{conflict}' already routes 26.x — "
            "remove it first"
        )
        line(f"Inspect with: ip link show {conflict}")
        go_back()
        return
    cached_ip = get_setting(cfg, "radmin_ip", "")
    radmin_ip = ask("Enter your RadminVPN IP", default=cached_ip or None)
    if not radmin_ip:
        return
    if not re.match(r"^26\.\d+\.\d+\.\d+$", radmin_ip):
        step_fail("Invalid IP")
        go_back()
        return
    set_setting(cfg, "radmin_ip", radmin_ip)
    save_config(cfg)

    subprocess.run(["sudo", "-v"], check=False)
    with Spinner("Creating bridge") as sp:
        error, changed, created = create_bridge(radmin_ip, ["sudo"])
        if error:
            sp.fail(f"Bridge setup failed — {error}")
        elif not verify_bridge(radmin_ip):
            sp.fail("Bridge verification failed")
        elif changed or created:
            sp.succeed("Bridge created")
        else:
            sp.warn("Bridge already active")
    go_back()


def _radmin_attach_vm() -> None:
    render_header("Attach VM to bridge")
    if not _has_command(VBOX_CMD):
        step_fail("Install VirtualBox first")
        go_back()
        return
    if not bridge_present():
        step_fail("Bridge not set up — run 'Create bridge' first")
        go_back()
        return

    vms = list_vms()
    if vms is None:
        step_fail("Could not list VirtualBox VMs")
        go_back()
        return
    if not vms:
        step_warn("No VirtualBox VMs found — create one first")
        go_back()
        return

    options = vms + ["Back"]
    pick = select("Pick VM", options)
    if pick is None or pick == len(options) - 1:
        return
    vm_name = vms[pick]

    clear()
    render_header("Attach VM to bridge")

    state = vm_state(vm_name)
    if state is None:
        step_fail(f"Could not read state of VM '{vm_name}'")
        go_back()
        return
    if state not in ("poweroff", "aborted"):
        step_fail(f"VM '{vm_name}' state is {state} — power it off first")
        go_back()
        return

    with Spinner("Configuring adapter") as sp:
        error = attach_vm(vm_name)
        if error:
            sp.fail(f"modifyvm failed — {error}")
            go_back()
            return
        sp.succeed(
            f"Adapter 2 of '{vm_name}' set to host-only on {VBOX_IFACE}"
        )
    go_back()


def _radmin_remove() -> None:
    render_header("Remove bridge")
    if not _has_command(VBOX_CMD):
        step_fail("Install VirtualBox first")
        go_back()
        return
    if not _has_command("sudo"):
        step_fail("Install sudo first")
        go_back()
        return
    if not bridge_present():
        step_warn(f"{VBOX_IFACE} doesn't exist")
        go_back()
        return
    step_warn(
        "Removing the bridge prevents the VM from starting until recreated"
    )
    if not confirm("Continue?", default=False):
        return
    clear()
    render_header("Remove bridge")
    subprocess.run(["sudo", "-v"], check=False)
    with Spinner("Removing bridge") as sp:
        error = remove_bridge(["sudo"])
        if error:
            sp.fail(f"Bridge removal failed — {error}")
        else:
            sp.succeed("Bridge removed")
    go_back()


def screen_radmin(cfg: dict) -> None:
    actions = [
        ("Create bridge",       lambda: _radmin_create(cfg)),
        ("Attach VM to bridge", _radmin_attach_vm),
        ("Remove bridge",       _radmin_remove),
    ]
    while True:
        radmin_ip = get_setting(cfg, "radmin_ip", "")
        ready = (
            bool(radmin_ip)
            and bridge_present()
            and verify_bridge(radmin_ip)
        )
        if ready:
            state = f"Bridge ready {C.MAG}✓{C.R}"
        else:
            state = f"Bridge not ready {C.ORN}✗{C.R}"
        options = [label for label, _ in actions] + ["Back"]
        pick = select(f"RadminVPN — {state}", options)
        if pick is None or pick == len(options) - 1:
            return
        clear()
        actions[pick][1]()
