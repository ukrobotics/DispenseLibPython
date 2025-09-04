import setuptools

# Read the contents of the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read the contents of the requirements file
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="DispenseLibDotPy",
    version="0.1.0",
    author="UK Robotics",
    description="A Python wrapper for the UK Robotics D2 dispenser.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UKRobotics/DispenseLibDotPy",
    packages=setuptools.find_packages(),
    include_package_data=True, # This tells setuptools to look for MANIFEST.in
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 4 - Beta",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    python_requires='>=3.7',
    install_requires=requirements,
)
