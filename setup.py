from setuptools import setup
from transfat.version import NAME, VERSION

setup(
    name=NAME,
    version=VERSION,
    description='Play audio files on your car stereo and maintain sanity',
    url='https://github.com/mwiens91/trans-fat',
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
    data_files=[('/usr/local/man/man1', ['extras/transfat.1']),],
    packages=['transfat', 'transfat.config'],
    package_data={'transfat.config': ['config.ini']},
    entry_points={
        'console_scripts': ['transfat = transfat.main:main'],
    },
)
