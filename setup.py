import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

name = "wappy"
version = "0.0.1"

setuptools.setup(
    name=name,
    version=version,
    author="Eloy Perez",
    author_email="eloy.perez@tarlogic.com",
    description="Discover web technologies in web applications "
    "from your terminal",
    url="https://github.com/blackarrowsec/wappy",
    project_urls={
        "Repository": "https://github.com/blackarrowsec/wappy",
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    entry_points={
        "console_scripts": [
            "wappy = wappy.main:main",
        ]
    },
    package_data={"wappy": ["technologies.json"]},
)
