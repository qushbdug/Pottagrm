#!/usr/bin/env python3
"""
Setup script for Yemen Net Bot
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README_PROFESSIONAL.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

setup(
    name="yemen-net-bot",
    version="3.0.0",
    author="Professional Development Team",
    author_email="support@yemennetbot.com",
    description="Professional Telegram bot for network card sales in Yemen",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/yemen-net-bot",
    project_urls={
        "Bug Tracker": "https://github.com/your-username/yemen-net-bot/issues",
        "Documentation": "https://github.com/your-username/yemen-net-bot/docs",
        "Source Code": "https://github.com/your-username/yemen-net-bot",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Topic :: Database",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "bandit>=1.7.0",
            "pre-commit>=3.0.0",
            "coverage>=7.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "myst-parser>=1.0.0",
        ],
        "performance": [
            "locust>=2.15.0",
            "pytest-benchmark>=4.0.0",
            "memory-profiler>=0.60.0",
            "line-profiler>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "yemen-net-bot=bot:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords=[
        "telegram",
        "bot",
        "yemen",
        "network",
        "cards",
        "payment",
        "wallet",
        "telecommunications",
        "arabic",
        "async",
        "sqlite",
        "financial",
    ],
    platforms=["any"],
    license="MIT",
    zip_safe=False,
)