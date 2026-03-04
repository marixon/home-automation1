from setuptools import setup, find_packages

setup(
    name="homeauto",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "sqlalchemy>=2.0.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.6",
        "websockets>=11.0",
    ],
    entry_points={
        "console_scripts": [
            "homeauto-scan=homeauto.cli.scan:main",
            "homeauto-config=homeauto.cli.config:main",
        ],
    },
)
