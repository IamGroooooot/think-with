# /// script
# requires-python = ">=3.12"
# dependencies = ["PyYAML==6.0.3"]
# ///
"""Validate the checkout without rewriting generated files."""

import argparse
import sys
import unittest

import yaml

from build import ROOT, output_differences, render_repository, validate_script


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        outputs = render_repository(ROOT)
        for script in sorted((ROOT / "scripts").glob("*.py")):
            validate_script(script.read_text(), script.name)
        differences = output_differences(ROOT, outputs)
        if differences:
            parser.exit(1, "Generated files differ; run mise run build:\n" + "\n".join(differences) + "\n")
    except (ValueError, OSError, SyntaxError, yaml.YAMLError) as error:
        parser.exit(1, f"check: {error}\n")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print(f"Checked {len(outputs)} generated files; tests passed.")


if __name__ == "__main__":
    main()
