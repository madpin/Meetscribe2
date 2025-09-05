#!/usr/bin/env python3
"""
Template Setup Validation Script

This script validates that placeholder replacement worked correctly
when someone uses this repository as a template.

Usage:
    python scripts/validate_setup.py [--fix]

Options:
    --fix    Automatically fix any remaining placeholders (dangerous!)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class SetupValidator:
    """Validates template setup and placeholder replacement."""

    PLACEHOLDERS = [
        "{{PROJECT_NAME}}",
        "{{OWNER_NAME}}",
        "{{REPO_NAME}}",
        "{{PROJECT_DESCRIPTION}}",
        "{{AUTHOR_NAME}}",
        "{{AUTHOR_EMAIL}}",
    ]

    # Files to check for placeholders
    CHECK_FILES = [
        "pyproject.toml",
        "config.toml",
        "README.md",
        ".github/workflows/ci.yml",
        ".github/workflows/template-setup.yml",
        "TEMPLATE_SETUP.md",
    ]

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def validate(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating template setup...\n")

        self._check_placeholders()
        self._check_project_structure()
        self._check_configuration()

        return self._report_results()

    def _check_placeholders(self):
        """Check for remaining placeholders in template files."""
        print("📝 Checking for remaining placeholders...")

        for file_path in self.CHECK_FILES:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text()
                for placeholder in self.PLACEHOLDERS:
                    if placeholder in content:
                        self.errors.append(
                            (f"Found placeholder {placeholder}", f"in {file_path}")
                        )
            except Exception as e:
                self.warnings.append((f"Could not read {file_path}", str(e)))

    def _check_project_structure(self):
        """Check that project structure is intact."""
        print("📁 Checking project structure...")

        required_files = [
            "app/__init__.py",
            "app/cli.py",
            "pyproject.toml",
            "config.toml",
            "README.md",
        ]

        for file_path in required_files:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                self.errors.append(("Missing required file", file_path))

    def _check_configuration(self):
        """Check that configuration files are valid."""
        print("⚙️  Checking configuration...")

        # Check pyproject.toml
        pyproject_path = self.root_dir / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if "name = " in content:
                # Extract project name
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if name_match:
                    project_name = name_match.group(1)
                    if project_name in [
                        "my-terminal-app",
                        "myapp",
                        "aio_terminal_template",
                        "{{PROJECT_NAME}}",
                    ]:
                        self.warnings.append(
                            (
                                "Project name may not be customized",
                                f"Current: {project_name}",
                            )
                        )

        # Check config.toml
        config_path = self.root_dir / "config.toml"
        if config_path.exists():
            content = config_path.read_text()
            if "github_repo = " in content:
                repo_match = re.search(
                    r'github_repo\s*=\s*["\']([^"\']+)["\']', content
                )
                if repo_match:
                    repo_value = repo_match.group(1)
                    if repo_value in [
                        "your-username/your-repo",
                        "{{OWNER_NAME}}/{{REPO_NAME}}",
                    ]:
                        self.warnings.append(
                            (
                                "GitHub repository reference may not be updated",
                                f"Current: {repo_value}",
                            )
                        )

    def _report_results(self) -> bool:
        """Report validation results."""
        success = len(self.errors) == 0

        if success:
            print("✅ Template setup validation PASSED!")
        else:
            print("❌ Template setup validation FAILED!")
            print("\n🚨 Critical Issues:")
            for error, detail in self.errors:
                print(f"   • {error}: {detail}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning, detail in self.warnings:
                print(f"   • {warning}: {detail}")

        if success:
            print("\n🎉 Your template setup looks good!")
            print("   You can now:")
            print("   • Run 'pip install -e .' to install dependencies")
            print("   • Run 'python -m app.cli --help' to test the CLI")
            print(
                "   • Run 'pyinstaller --onefile --name <your-app> app/cli.py' to build"
            )

        return success

    def fix_placeholders(self, dry_run: bool = True) -> bool:
        """Attempt to fix remaining placeholders."""
        if not self.errors:
            print("✅ No placeholders to fix!")
            return True

        print("🔧 Attempting to fix placeholders...")

        # This is a basic implementation - in practice, you'd want more sophisticated logic
        # to determine the correct replacement values

        print("⚠️  Automatic fixing is not implemented yet.")
        print("   Please manually replace the placeholders listed above.")

        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate template setup")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--root", default=".", help="Root directory to check")

    args = parser.parse_args()

    validator = SetupValidator(args.root)

    if args.fix:
        success = validator.fix_placeholders()
    else:
        success = validator.validate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
