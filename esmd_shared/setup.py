from setuptools import setup, find_packages

setup(
    name='esmd_shared',  # Name of the shared package
    version='2.0.0',  # Package version
    description='Shared utilities and core functionality for EsmdFHIRClient',
    author='Srini',
    author_email='srinivase@c-hit.com',
    url='',  # Project URL (optional)
    packages=find_packages(),  # Automatically find packages in the directory
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',  # Minimum Python version required
    install_requires=[
        'requests>=2.31.0',
        'pyyaml>=6.0.1',
        'python-dotenv>=1.0.0',
        'typing-extensions>=4.6.0'
    ],
    # Package data
    package_data={
        '': ['*.py'],
    },
    # Include all Python files
    include_package_data=True,
    # Make this package available to other modules
    zip_safe=False,
) 