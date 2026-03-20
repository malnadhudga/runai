from setuptools import setup, find_packages

setup(
    name="runai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv"
    ],
    entry_points={
        'console_scripts': [
            'runai = runai.cli.main:main',
        ],
    },
    author="Ketan Hegde",
    description="CLI for multi-agent AI coding (planner, workers, review, assemble)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
