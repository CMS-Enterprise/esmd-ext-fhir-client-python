"""
Setup configuration for EsmdFHIRClient package.

This package provides comprehensive FHIR client capabilities for esMD services
including bundle submission, document reference management, practitioner 
registration, and notification handling.
"""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='esmd-fhir-client',
    version='1.0.0',
    description='Comprehensive FHIR client for esMD services',
    long_description=long_description,
    long_description_content_type='text/markdown',
    
    # Author information
    author='EsmdFHIRClient Team',
    author_email='srinivase@c-hit.com',
    maintainer='EsmdFHIRClient Team',
    maintainer_email='srinivase@c-hit.com',
    
    # Project URLs
    url='https://github.com/your-org/esmd-fhir-client',
    project_urls={
        'Bug Reports': 'https://github.com/your-org/esmd-fhir-client/issues',
        'Source': 'https://github.com/your-org/esmd-fhir-client',
        'Documentation': 'https://github.com/your-org/esmd-fhir-client#readme',
    },
    
    # Package discovery
    packages=find_packages(include=[
        'esmd_shared',
        'esmd_shared.*',
        'bundlesubmissionclient',
        'bundlesubmissionclient.*',
        'documentrefscheduler',
        'documentrefscheduler.*',
        'notificationscheduler',
        'notificationscheduler.*',
        'practitionerclient',
        'practitionerclient.*'
    ]),
    
    # Package data
    package_data={
        '': ['*.yaml', '*.yml', '*.txt', '*.md'],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=requirements,
    
    # Ensure shared module is installed first
    dependency_links=[],
    
    # Optional dependencies for development
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
        ],
        'docs': [
            'sphinx>=7.1.0',
            'sphinx-rtd-theme>=1.3.0',
        ],
        'testing': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.11.0',
            'requests-mock>=1.11.0',
        ]
    },
    
    # Entry points for command-line tools
    entry_points={
        'console_scripts': [
            'esmd-bundle-submit=bundlesubmissionclient.cli:main',
            'esmd-practitioner=practitionerclient.cli:main',
            'esmd-docref-scheduler=documentrefscheduler.cli:main',
            'esmd-notification-scheduler=notificationscheduler.cli:main',
        ],
    },
    
    # Python version requirement
    python_requires='>=3.9',
    
    # PyPI classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Typing :: Typed',
    ],
    
    # Keywords for PyPI search
    keywords=[
        'fhir', 'healthcare', 'hl7', 'interoperability', 
        'esmd', 'cms', 'medical', 'api', 'client'
    ],
    
    # Zip safety
    zip_safe=False,
    
    # Additional metadata
    platforms=['any'],
    license='MIT',
) 