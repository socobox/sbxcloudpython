import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sbxpy",
    version="0.8.0",
    author="Luis Guzmán",
    author_email="lgguzman890414@gmail.com",
    description="This is the module  create all request used to communicate with SbxCloud",
    long_description="This is the module  create all request used to communicate with SbxCloud",
    long_description_content_type="text/markdown",
    url="https://github.com/sbxcloud/sbxcloudpython",
    packages=setuptools.find_packages(),
    install_requires=[
              'aiohttp>=3.7.3',
              'redis>=4.5.2',
              'pydantic>2.1.0',
              'deepmerge>=1.1.0'
          ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
