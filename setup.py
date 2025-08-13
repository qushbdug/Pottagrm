#!/usr/bin/env python3
"""
Setup script for Yemen Net Bot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read minimal requirements for production
with open("requirements-minimal.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="yemen-net-bot",
    version="2.0.0",
    author="Yemen Net Team",
    author_email="support@yemen-net.com",
    description="نظام بوت تليجرام متطور لبيع كروت الشبكة",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/yemen-net-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "yemen-net-bot=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)