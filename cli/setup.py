from setuptools import setup, find_packages

setup(
    name="crew",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv"
    ],
    entry_points={
        'console_scripts': [
            'crew = crew.cli.main:main',
        ],
    },
    author="Ketan Hegde",
    description="A CLI tool that runs a crew of GPT-based coding agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
