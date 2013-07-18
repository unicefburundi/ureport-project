'''
Created on Nov April, 2013

@author: asseym
'''

from django.core.management.base import BaseCommand
from ureport.init_scripts import init_structures

class Command(BaseCommand):
    def handle(self, **options):
        init_structures()
        self.stdout.write('')
        self.stdout.write('done!')
