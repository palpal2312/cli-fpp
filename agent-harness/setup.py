#!/usr/bin/env python3
"""setup.py for cli-fpp."""

from setuptools import find_packages, setup

with open("cli_fpp/README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cli-fpp",
    version="0.1.0",
    author="palpal2312",
    description="Command-line client for Falcon Player (FPP) via REST API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/palpal2312/cli-fpp",
    packages=find_packages(include=["cli_fpp", "cli_fpp.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-fpp=cli_fpp.cli:main",
        ],
    },
    package_data={
        "cli_fpp": ["skills/*.md"],
    },
    include_package_data=True,
    zip_safe=False,
)
