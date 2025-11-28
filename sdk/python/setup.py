"""Setup script for eje-client package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="eje-client",
    version="1.0.0",
    author="Eleanor Project Contributors",
    author_email="eleanor-project@example.com",
    description="Python client for the Eleanor Judicial Engine (EJE) API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eleanor-project/EJE",
    project_urls={
        "Bug Tracker": "https://github.com/eleanor-project/EJE/issues",
        "Documentation": "https://eleanor-project.github.io/EJE/",
        "Source Code": "https://github.com/eleanor-project/EJE",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
    },
    package_data={
        "eje_client": ["py.typed"],
    },
    zip_safe=False,
)
