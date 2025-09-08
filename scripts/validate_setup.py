#!/usr/bin/env python3
"""
Project Setup Validation Script

This script validates that the project is properly configured and all
necessary files are present.

Usage:
    python scripts/validate_setup.py [--fix]

Options:
    --fix    Automatically fix any configuration issues (dangerous!)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class SetupValidator:
    """Validates project setup and configuration."""

    # Files to check for basic validity
    CHECK_FILES = [
        "pyproject.toml",
        "config.toml",
        "README.md",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        "app/cli.py",
        "app/__init__.py",
    ]

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def validate(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating project setup...\n")

        self._check_project_structure()
        self._check_configuration()
        self._check_workflows()

        return self._report_results()

    def _check_placeholders(self):
        """Check for remaining placeholders in project files."""
        print("📝 Checking for configuration placeholders...")

        placeholder_patterns = [
            r"your-username/your-repo",
            r"your-email@example\.com",
            r"your-project-name"
        ]

        for file_path in self.CHECK_FILES:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text()
                for pattern in placeholder_patterns:
                    if re.search(pattern, content):
                        self.warnings.append(
                            (f"Found placeholder pattern '{pattern}'", f"in {file_path}")
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

    def _check_workflows(self):
        """Check that GitHub workflows are properly configured."""
        print("🔄 Checking GitHub workflows...")

        workflow_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/release.yml"
        ]

        for workflow_file in workflow_files:
            workflow_path = self.root_dir / workflow_file
            if not workflow_path.exists():
                self.errors.append(("Missing workflow file", workflow_file))
                continue

            try:
                content = workflow_path.read_text()
                # Check for basic workflow validity
                if "jobs:" not in content:
                    self.errors.append(("Invalid workflow format", f"{workflow_file} missing jobs section"))
                if "runs-on:" not in content:
                    self.errors.append(("Invalid workflow format", f"{workflow_file} missing runs-on"))
            except Exception as e:
                self.warnings.append((f"Could not validate {workflow_file}", str(e)))

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
                    if not project_name or project_name == "":
                        self.errors.append(("Invalid project name", "Project name cannot be empty"))
                    elif project_name in ["myapp", "your-app"]:
                        self.warnings.append(
                            ("Generic project name detected", f"Consider customizing: {project_name}")
                        )

            # Check for version
            if "version = " not in content:
                self.errors.append(("Missing version", "pyproject.toml should specify a version"))

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
                    if repo_value in ["your-username/your-repo"]:
                        self.warnings.append(
                            ("GitHub repository not configured", f"Update config.toml: {repo_value}")
                        )

    def _report_results(self) -> bool:
        """Report validation results."""
        success = len(self.errors) == 0

        if success:
            print("✅ Project setup validation PASSED!")
        else:
            print("❌ Project setup validation FAILED!")
            print("\n🚨 Critical Issues:")
            for error, detail in self.errors:
                print(f"   • {error}: {detail}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning, detail in self.warnings:
                print(f"   • {warning}: {detail}")

        if success:
            print("\n🎉 Your project setup looks good!")
            print("   You can now:")
            print("   • Run 'pip install -e .' to install dependencies")
            print("   • Run 'python -m app.cli --help' to test the CLI")
            print("   • Run './scripts/release.sh' to create a new release")

        return success

    def fix_placeholders(self, dry_run: bool = True) -> bool:
        """Attempt to fix remaining configuration issues."""
        if not self.errors:
            print("✅ No issues to fix!")
            return True

        print("🔧 Attempting to fix configuration issues...")

        # This is a basic implementation - in practice, you'd want more sophisticated logic
        # to determine the correct replacement values

        print("⚠️  Automatic fixing is not implemented yet.")
        print("   Please manually resolve the issues listed above.")

        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate project setup")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix configuration issues")
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
