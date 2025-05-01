import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), "r") as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="marknote",
    version="0.1.0",
    description="A command-line tool for creating, organizing, and managing Markdown-based notes",
    author="Admas Terefe Girma",
    author_email="aadmasterefe00@gmail.com",
    url="https://github.com/Son-OfAnton/MarkNote.git",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "marknote=app.__main__:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Office Suites",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="markdown, notes, cli, organization",
)