from setuptools import setup

setup(
    name='transfat',
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
    packages=['transfat', 'transfat.config'],
    package_data={'transfat.config': ['config.ini']},
    entry_points={
        'console_scripts': ['transfat = transfat.main:main'],
    },
)
