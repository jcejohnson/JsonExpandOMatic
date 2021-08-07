
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='json_expand_o_matic',

    version='0.1.3',

    description='Expand a dict into a collection of subdirectories and json files or '
                'contract (un-expand) the output of expand() into a dict.',

    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/jcejohnson/JsonExpandOMatic',

    author='James Johnson',
    author_email='jcejohnson@users.noreply.github.com',

    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        # "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],

    keywords='json, jsonref',

    package_dir={'': 'src'},
    packages=find_packages(where='src'),  # Required

    install_requires=(here / 'requirements.txt').read_text(encoding='utf-8').split('\n'),

    entry_points={  # Optional
        'console_scripts': [
            'JsonExpandOMatic=json_expand_o_matic.cli:main'
        ],
    },
)
