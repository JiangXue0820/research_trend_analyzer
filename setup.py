from setuptools import setup, find_packages

setup(
    name="research_trend_analyzer_light",
    version="0.1.0",
    description="A lightweight tool for analyzing research trends.",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here, e.g.:
        # "numpy>=1.21.0",
        # "pandas>=1.3.0",
    ],
    python_requires=">=3.7",
)