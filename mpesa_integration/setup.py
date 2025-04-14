from setuptools import setup, find_packages
import os

# Get the directory of the current script
current_dir = os.path.abspath(os.path.dirname(__file__))

# Construct the path to the README.md file
readme_path = os.path.join(current_dir, '..', 'README.md')

setup(
    name="mpesa-integration",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
    ],
    author="thought vision",
    author_email="arapbiisubmissions@gmail.com",
    description="A Python package for M-Pesa STK Push integration (Till and Paybill)",
    long_description=open(readme_path, encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/seven7-AI/mpesa-integration",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
