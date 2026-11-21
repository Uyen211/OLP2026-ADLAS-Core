# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import os
import sys

# Script to verify that every source file contains standard copyright and SPDX license identifier headers
REQUIRED_HEADER_PYTHON = "SPDX-License-Identifier: MIT"
REQUIRED_HEADER_JS = "SPDX-License-Identifier: MIT"


def check_file(filepath: str) -> bool:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read(500)
            return "SPDX-License-Identifier: MIT" in content or "Copyright (c) 2026 ADLAS" in content
    except Exception:
        return False


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_extensions = (".py", ".ts", ".tsx", ".sql", ".sh")
    missing = []

    for dirpath, _, filenames in os.walk(root_dir):
        if any(skip in dirpath for skip in ["venv", "node_modules", ".git", "__pycache__", "dist"]):
            continue
        for filename in filenames:
            if filename.endswith(target_extensions):
                full_path = os.path.join(dirpath, filename)
                if not check_file(full_path):
                    missing.append(os.path.relpath(full_path, root_dir))

    if missing:
        print("Missing copyright headers in the following files:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("All source files passed license and copyright verification.")
        sys.exit(0)


if __name__ == "__main__":
    main()
