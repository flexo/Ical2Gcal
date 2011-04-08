from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='Ical2GCal',
      version=version,
      description="Send .ics invites to Google Calendar",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Nick Murdoch',
      author_email='nick@nivan.net',
      url='http://nivan.net/nickmurdoch',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
