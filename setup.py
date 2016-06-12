from setuptools import setup, find_packages

setup(
    name="threedub",
    version="0.1",
    description="Python port of ThreeDubber",
    packages=find_packages(),
    install_requires=[
        "Crypto",
        "Padding",
    ],
    tests_require=["nose"],
    test_suite="nose.collector",
    entry_points={
        "console_scripts": [
            "threedub = threedub.main:threedub",
        ]
    },
)
