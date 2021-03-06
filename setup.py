import setuptools

setuptools.setup(
    name="compress-asgi",
    version="0.1.0",
    author="Kuba Sawulski",
    author_email="kuba@sawul.ski",
    description="Compress ASGI middleware with minimal dependencies",
    url="https://github.com/kubasaw/compress-asgi",
    project_urls={
        "Bug Tracker": "https://github.com/kubasaw/compress-asgi/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["compress_asgi"],
    package_dir={"compress_asgi": "compress_asgi"},
    python_requires=">=3.7",
    extras_require={
        "brotli": ["brotli>=1.0.9,<2"],
    },
)
