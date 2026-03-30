from setuptools import setup, find_packages

setup(
    name="minibench",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1",
        "psutil>=5.9",
        "requests>=2.31",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "minibench=minibench.cli:main",
        ],
    },
    python_requires=">=3.10",
    author="RaapTech LLC",
    description="CLI benchmark tool for Mini PCs running local LLMs",
)
