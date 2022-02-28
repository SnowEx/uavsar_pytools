import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="uavsar_pytools",
    version="1.0.0",
    description="Download and convert UAVSAR grd files",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/SnowEx/uavsar_pytools",
    author="Zach Keskinen & Jack Tarricone",
    author_email="zachkeskinen@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["uavsar_pytools"],
    include_package_data=True,
    install_requires=["feedparser", "html2text"],
    entry_points={
        "console_scripts": [
            "realpython=reader.__main__:main",
        ]
    },
)