from setuptools import setup
from transfat.version import NAME, VERSION


# Parse readme to include in PyPI page
with open('README.md') as f:
    long_description = f.read()

setup(
    name=NAME,
    version=VERSION,
    description='Play audio files on your car stereo and maintain sanity',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mwiens91/transfat',
    author='Matt Wiens',
    author_email='mwiens91@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3 :: Only',
    ],
    data_files=[('/usr/local/man/man1', ['man/transfat.1']),],
    packages=['transfat', 'transfat.config'],
    package_data={'transfat.config': ['config.ini', 'transfatrc']},
    entry_points={
        'console_scripts': ['transfat = transfat.main:main'],
    },
)
