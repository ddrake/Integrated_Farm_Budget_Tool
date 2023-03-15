import setuptools

setuptools.setup(
    name='ifbt',
    version='0.1.1',
    description=('Integrated Farm Budget Tool: An integrated tool ' +
                 'allowing midwest grain farmers to budget farm ' +
                 'profitability and readily visualize outcomes ' +
                 'sensitized to price and yield.'),
    classifiers=[
        "Programming Language :: Python :: 3"
        "License :: OSI Approved :: BSD3 License",
        "Operating System :: OS Independent",
    ],
    url='#',
    author='Integrated Farm Budget Tool Team',
    install_requires=['tabulate'],
    author_email='',
    packages=setuptools.find_packages(),
    package_data={'ifbt': ['data/*.txt']},
    zip_safe=False)
