"""Legacy setup.py for environments that require it (e.g. pip < 21)."""

from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup


PACKAGE_NAME = "lead-enricher"
VERSION = "0.1.0"
DESCRIPTION = "Offline-friendly scaffolding for enriching UK roofing business leads"
AUTHOR = "Lead Enricher Dev Team"


def read_long_description() -> str:
    readme_path = Path(__file__).resolve().parent / "README.md"
    return readme_path.read_text(encoding="utf-8")


setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author=AUTHOR,
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[],
    entry_points={
        "console_scripts": [
            "lead-enricher=lead_enricher.cli:main",
            "lead-enricher-gui=lead_enricher.gui:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
    ],
)
