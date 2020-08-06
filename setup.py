from setuptools import find_packages, setup

setup(
    name='AJNA-bhadrasana',
    description='Visao computacional e Aprendizado de Maquina na Vigilancia Aduaneira',
    version='0.0.1',
    url='https://github.com/IvanBrasilico/bhadrasana',
    license='GPL',
    author='Ivan Brasilico',
    author_email='brasilico.ivan@gmail.com',
    packages=find_packages(),
    install_requires=[
        'chardet',
        'dominate',
        'defusedxml',
        'Flask',
        'flask-admin',
        'flask-babelex',
        'Flask-BootStrap',
        'Flask-Login',
        'Flask-cors',
        'Flask-nav',
        'Flask-session',
        'Flask-wtf',
        'gunicorn',
        'lxml',
        'Pillow',   # Centralizar acesso imagens no virasana??
        'plotly', # Ver como retirar necessidade
        'odfpy',
        'pymongo',
        'pymysql',
        'redis', # Ver como retirar necessidade
        'requests', # Ver como retirar necessidade
        'sqlalchemy',
        'xlrd',
        'xlwt',
    ],
    dependency_links=[
        'git+https://github.com/IvanBrasilico/ajna_commons.git#egg=ajna_commons-0.0.1'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    test_suite="tests",
    package_data={
    },
    extras_require={
        'dev': [
            'alembic',
            'bandit',
            'coverage',
            'flake8',
            'flake8-docstrings',
            'flake8-quotes',
            'flake8-todo',
            'flask-webtest',
            'flask-testing',
            'isort',
            'autopep8',
            'mkdocs',
            'mkdocs-material',
            'pandas',
            'pylint',
            'pytest',
            'pytest-cov',
            'pytest-mock',
            'radon',
            'testfixtures',
            'tox',
            'mongomock'
        ],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3.5',
    ],
)
