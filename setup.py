from setuptools import setup, find_packages

setup(
    name="hcr",
    version="0.2.0",
    description="Hybrid Cognitive Runtime — State-based cognitive execution system",
    author="PantheraLabs",
    url="https://github.com/PantheraLabs/HybridCognitiveRuntime",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
        "pyyaml>=6.0",
        "rich>=13.0",
    ],
    extras_require={
        "groq": ["groq>=0.11.0"],
        "google": ["google-genai>=1.0.0"],
        "anthropic": ["anthropic>=0.40.0"],
        "openai": ["openai>=1.0.0"],
        "all": ["groq>=0.11.0", "google-genai>=1.0.0", "anthropic>=0.40.0", "openai>=1.0.0"],
    },
    entry_points={
        "console_scripts": [
            "hcr=product.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
)
