from setuptools import setup

setup(
    name='feedmailer',
    description='A commandline application for emailing rss feeds',
    version='0.0.1',
    url='https://gitlab.com/jgoss/feed-mailer',
    author='Joshua Goss',
    author_email='josh@joshgoss.com',
    scripts=['bin/feedmailer'],
    zip_safe=False,
    include_package_data=True,
    packages=['feedmailer'],
    package_data={'feedmailer': [
        'data/defaults.cfg',
        'data/article.txt.jinja',
        'data/digest.txt.jinja',
        'data/digest.html.jinja',
        'data/article.html.jinja'
    ]},
    license='GPL3',
    keywords='rss email feeds'

)
