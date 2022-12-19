from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

with open('requirements_dev.txt') as f:
    required = f.read().splitlines()
    print(required)
setup(
    name="antiplagiat-api",
    version="0.0.1",
    author="C15HOT",
    author_email="wvxp@mail.ru",
    description="Antiplagiat API",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/C15HOT/antiplagiat_api",
    packages=find_packages(),
    install_requires=required,
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)