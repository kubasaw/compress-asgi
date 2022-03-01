import setuptools

setuptools.setup(
    name="compress-asgi",
    version="0.0.1",
    author="Kuba Sawulski",
    author_email="kuba@sawul.ski",
    description="A small example package",
    url="https://github.com/kubasaw/compress-asgi",
    project_urls={
        "Bug Tracker": "https://github.com/kubasaw/compress-asgi/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(exclude='tests*'),
    python_requires=">=3.7",
)
