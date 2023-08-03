from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

setup(
  name="packnow",
  author="AWeirdDev",
  version="1.2",
  license="MIT License",
  description="Pack everything, now. Cross-platform.",
  long_description=readme,
  long_description_content_type="text/markdown",
  author_email="aweirdscratcher@gmail.com",
  packages=['packnow'],
  classifiers=[
    "Programming Language :: Python :: 3.9",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Environment :: Console",
  ],
  keywords=["pack", "packing", "packnow"],
  entry_points={
    "console_scripts": [
      "packnow=packnow.main:main"
    ]
  },
  install_requires=[
      "zipfile", 
      "termcolor", 
      "fastapi", 
      "questionary", 
      "websockets", 
      "uvicorn"
  ]
)
