import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def main() -> None:
    project_root = Path(__file__).resolve().parent
    venv_dir = project_root / ".venv"

    # 1. Create virtual environment if it doesn't exist
    if not venv_dir.exists():
        print(f"[INFO] Creating virtual environment at {venv_dir} ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print(f"[INFO] Virtual environment already exists at {venv_dir}.")

    # 2. Resolve the venv's Python executable (OS-independent)
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        raise RuntimeError(f"Could not find venv python at {venv_python}")

    # 3. Install dependencies from face_attendance/requirements.txt using venv Python
    requirements_path = project_root / "face_attendance" / "requirements.txt"
    if not requirements_path.exists():
        raise FileNotFoundError(f"requirements.txt not found at {requirements_path}")

    print(f"[INFO] Upgrading pip in the virtual environment...")
    subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    print(f"[INFO] Installing dependencies from {requirements_path} ...")
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements_path)]
    )

    # 3b. Patch face_recognition_models __init__.py on disk (no import needed)
    print("[INFO] Applying compatibility patch to face_recognition_models (if installed)...")

    def find_site_packages(base: Path) -> Optional[Path]:
        lib_dir = base / "lib"
        if not lib_dir.exists():
            return None
        for sub in lib_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("python"):
                sp = sub / "site-packages"
                if sp.is_dir():
                    return sp
        return None

    site_packages = find_site_packages(venv_dir)
    if site_packages is not None:
        init_path = site_packages / "face_recognition_models" / "__init__.py"
        if init_path.exists():
            src = init_path.read_text(encoding="utf-8")
            marker = "from pkg_resources import resource_filename"
            if "# Patched by setup_env.py" in src:
                print("[INFO] face_recognition_models already patched.")
            elif marker in src:
                replacement = """# Patched by setup_env.py to avoid hard dependency on pkg_resources.
try:
    from pkg_resources import resource_filename  # type: ignore
except ImportError:  # pragma: no cover
    from importlib.resources import files

    def resource_filename(package_or_requirement, resource_name):
        return str(files(package_or_requirement) / resource_name)
"""
                init_path.write_text(src.replace(marker, replacement), encoding="utf-8")
                print(f"[INFO] Patched {init_path}")
            else:
                print("[INFO] No pkg_resources import found in face_recognition_models; skipping patch.")
        else:
            print("[INFO] face_recognition_models not found in site-packages; skipping patch.")
    else:
        print("[INFO] Could not locate site-packages to patch face_recognition_models.")

    # 4. Show activation instructions (cannot persistently activate from inside Python)
    print("\n[INFO] Setup complete.")
    print("[INFO] To activate the virtual environment in your shell, run:")
    if os.name == "nt":
        print(r"  .venv\Scripts\activate")
    else:
        print("  source .venv/bin/activate")

    print("\n[INFO] Then you can run your app, for example:")
    print("  python face_attendance/test_register.py")


if __name__ == "__main__":
    main()

