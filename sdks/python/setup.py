from setuptools import setup, find_packages

setup(
    name="aetherai",
    version="2026.7.0",
    description="AetherAI Platform Python SDK",
    author="AetherAI Team",
    packages=find_packages(),
    install_requires=["httpx>=0.27.0", "pydantic>=2.8.0"],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
