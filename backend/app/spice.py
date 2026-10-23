"""Run fixed, generated netlists; validate numerical output, not just exit codes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

import numpy as np
from scipy import signal

from .engineering import components, transfer, noise_budget
from .schemas import SimulationConfig
from .artifacts import output_root

ROOT = Path(__file__).resolve().parents[2]
LOCK = threading.Lock()


def solver():
    configured = os.environ.get("NGSPICE_EXE")
    if configured:
        return Path(configured).resolve()
    local = ROOT / ".tools/ngspice41/Fusion360-Update/ngspice/bin/ngspice.exe"
    found = shutil.which("ngspice")
    return local if local.is_file() else Path(found) if found else None


def netlists(c):
    lines = ["Ideal-buffer Sallen-Key candidate; no device model or notch", f".temp {c.temperature_c}", "Vin input 0 DC 0 AC 1 PULSE(0 0.001 0.01 1u 1u 0.05 0.1)", "Eina stage0 0 input 0 9.998178506375227"]
    previous = "stage0"
    for i, stage in enumerate(components(c)):
        n1, n2, out = f"n{i}a", f"n{i}b", f"stage{i+1}"
        if stage["kind"] == "highpass":
            lines += [f"C{i}1 {previous} {n1} {stage['c1_f']:.15g}", f"C{i}2 {n1} {n2} {stage['c2_f']:.15g}", f"R{i}1 {n1} {out} {stage['r1_ohm']:.15g}", f"R{i}2 {n2} 0 {stage['r2_ohm']:.15g}"]
        else:
            lines += [f"R{i}1 {previous} {n1} {stage['r1_ohm']:.15g}", f"R{i}2 {n1} {n2} {stage['r2_ohm']:.15g}", f"C{i}1 {n1} {out} {stage['c1_f']:.15g}", f"C{i}2 {n2} 0 {stage['c2_f']:.15g}"]
        lines.append(f"Ebuffer{i} {out} 0 {n2} 0 1")
        previous = out
    lines += [f"Epost out 0 {previous} 0 {c.post_gain}", ".control", "set noaskquit", "set wr_singlescale", "set wr_vecnames", "ac dec 100 1 10000", "wrdata ideal-ac.txt v(out)", "tran 0.00005 0.15", "wrdata ideal-transient.txt v(input) v(out)", "noise v(out) Vin lin 1001 20 450 1", "setplot noise1", "wrdata ideal-noise.txt onoise_spectrum", "quit", ".endc", ".end"]
    ideal = "\n".join(lines)+"\n"
    devices = f"""TI macro-model isolated amplifier checks; not full-chain validation
.temp {c.temperature_c}
.include "{(ROOT / 'circuits/models/INA826-pspice.lib').as_posix()}"
.include "{(ROOT / 'circuits/models/OPA2376.lib').as_posix()}"
Vdd vdd 0 3.3
Vref ref 0 1.65
Vp inp 0 DC 1.65005 AC 0.5
Vn inn 0 DC 1.64995 AC -0.5
Xina inp inn rgp rgm vdd 0 ina ref INA826
Rg rgm rgp 5490
Rload ina ref 10k
Vsig signal 0 DC 0.0001 AC 1
Eoffset postin ref signal 0 1
Xpost postin neg vdd 0 post OPAx376
Rf post neg {max(1e-9, (c.post_gain-1)*1000):.15g}
Rb neg ref 1000
Rl post ref 10k
.control
set noaskquit
set wr_singlescale
set wr_vecnames
op
print v(ina) v(post)
ac dec 50 1 1000000
wrdata device-ac.txt v(ina) v(post)
dc Vsig -0.05 0.05 0.0005
wrdata post-dc.txt v(post)
quit
.endc
.end
"""
    return {"ideal": ideal, "devices": devices}


def run(c: SimulationConfig):
    exe = solver()
    if exe is None or not exe.is_file():
        return {"status": "unavailable", "reason": "ngspice executable unavailable; run scripts/prepare_spice.py", "config": c.model_dump()}
    if not LOCK.acquire(blocking=False):
        return {"status": "busy", "reason": "Another SPICE verification is running"}
    try:
        directory = output_root() / "results/spice"
        directory.mkdir(parents=True, exist_ok=True)
        cm = exe.parent.parent / "lib/ngspice"
        init = "set ngbehavior=ps\n"
        if cm.is_dir():
            # Relative paths avoid ngspice Windows code-model quoting issues.
            for name in ["spice2poly.cm", "analog.cm", "table.cm"]:
                try:
                    path = Path(os.path.relpath(cm / name, directory)).as_posix()
                except ValueError:
                    shutil.copyfile(cm / name, directory / name)
                    path = name
                init += f"codemodel {path}\n"
        (directory / ".spiceinit").write_text(init, encoding="ascii")
        report = {"status": "partial", "config": c.model_dump(), "solver": exe.name, "checks": {}, "limitations": "Ideal-buffer circuit excludes notch, rails and device nonidealities. TI amplifier checks are isolated; compatibility is judged by expected gain. No human hardware validation."}
        for name, text in netlists(c).items():
            if name == "devices" and not all((ROOT / "circuits/models" / model).is_file() for model in ["INA826-pspice.lib", "OPA2376.lib"]):
                report["checks"][name] = {"status": "unavailable", "reason": "Download TI models with scripts/prepare_spice.py"}
                continue
            (directory / f"{name}.cir").write_text(text, encoding="ascii")
            outputs = ["ideal-ac.txt", "ideal-transient.txt", "ideal-noise.txt"] if name == "ideal" else ["device-ac.txt", "post-dc.txt"]
            for filename in outputs:
                (directory / filename).unlink(missing_ok=True)
            try:
                completed = subprocess.run([str(exe), "-b", "-o", f"{name}.log", f"{name}.cir"], cwd=directory, capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                log = (directory / f"{name}.log").read_text(errors="replace")
                check = {"status": "failed", "exit_code": completed.returncode, "solver_banner": completed.stdout.decode(errors="replace")[:500], "log": f"results/spice/{name}.log"}
                if completed.returncode == 0 and all((directory / f).is_file() for f in outputs):
                    if name == "ideal":
                        transient = np.loadtxt(directory / outputs[1], skiprows=1, ndmin=2)
                        if (transient.shape[1] != 3 or len(transient) < 3
                                or not np.isfinite(transient).all()
                                or not np.all(np.diff(transient[:, 0]) > 0)
                                or abs(transient[0, 0]) > 1e-9
                                or abs(transient[-1, 0] - 0.15) > 1e-6):
                            raise ValueError("Invalid transient: expected finite time/input/output columns and increasing time spanning 0–0.15 s")
                        data = np.loadtxt(directory / outputs[0], skiprows=1)
                        f = data[:, 0]
                        actual = data[:, 1]+1j*data[:, 2]
                        expected = np.full(len(f), (1+49400/5490)*c.post_gain, complex)
                        for stage in components(c):
                            expected *= signal.freqs(*transfer(stage), worN=2*np.pi*f)[1]
                        error = float(np.max(np.abs(20*np.log10(np.abs(actual/expected)))))
                        noise_data = np.loadtxt(directory / outputs[2], skiprows=1)
                        actual_noise = float(np.sqrt(np.trapezoid(noise_data[:, 1]**2, noise_data[:, 0])))
                        budget = noise_budget(c.model_copy(update={"notch": False}))
                        expected_noise = float(np.sqrt(sum(part["output_rms_v"]**2 for part in budget["contributions"] if part["source"] in ["HP resistors", "LP1 resistors", "LP2 resistors"])))
                        noise_error = abs(actual_noise/expected_noise-1)
                        check.update({"status": "passed" if error < 0.01 and noise_error < 0.01 else "failed", "transient_samples": len(transient), "max_magnitude_error_db": error, "samples": len(f), "spice_filter_resistor_noise_rms_v": actual_noise, "analytical_filter_resistor_noise_rms_v": expected_noise, "noise_relative_error": noise_error})
                    else:
                        data = np.loadtxt(directory / outputs[0], skiprows=1)
                        i = np.argmin(abs(data[:, 0]-100))
                        ina = float(np.hypot(data[i, 1], data[i, 2]))
                        post = float(np.hypot(data[i, 3], data[i, 4]))
                        dc = np.loadtxt(directory / outputs[1], skiprows=1)
                        ideal_dc = 1.65+c.post_gain*dc[:, 0]
                        linear = (ideal_dc >= 0.2) & (ideal_dc <= 3.1)
                        dc_error = float(np.max(np.abs(dc[linear, 1]-ideal_dc[linear])))
                        ina_valid = abs(ina/(1+49400/5490)-1) < 0.05
                        post_valid = abs(post/c.post_gain-1) < 0.05 and dc_error < 0.02
                        check.update({"status": "passed" if ina_valid and post_valid else "failed", "ina_gain_100hz": ina, "ina_expected_gain": 1+49400/5490, "post_gain_100hz": post, "post_expected_gain": c.post_gain, "ina_valid": ina_valid, "post_valid": post_valid, "warning": "Failed gain checks mean this compatibility run is not device validation; inspect solver log and use a supported TI simulator."})
                        check.update({"post_dc_output_range_v": [float(dc[:, 1].min()), float(dc[:, 1].max())], "post_dc_linear_max_error_v": dc_error})
                if "Warning:" in log or "Error" in log:
                    check["solver_warnings"] = True
                report["checks"][name] = check
            except (subprocess.TimeoutExpired, OSError, ValueError) as error:
                report["checks"][name] = {"status": "failed", "reason": str(error)}
        checks = report["checks"].values()
        report["status"] = "passed" if all(check["status"] == "passed" for check in checks) else "partial" if any(check["status"] == "passed" or check.get("post_valid") or check.get("ina_valid") for check in checks) else "failed"
        (directory / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        LOCK.release()
