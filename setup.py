from setuptools import setup, find_packages

setup(
    name="devops-project-git-archiver",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyGitHub>=2.3.0",
        "python-dotenv>=1.0.1",
        "Jinja2>=3.1.4",
    ],
)
