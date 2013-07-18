'''
Created on Apr 15, 2013

@author: asseym
'''

import xlrd
from optparse import OptionParser, make_option
import datetime

from django.core.management.base import BaseCommand
from rapidsms.contrib.locations.models import Location, LocationType, Point

class Command(BaseCommand):


    option_list = BaseCommand.option_list + (
    make_option("-f", "--file", dest="path"),

    )
    
    def handle(self, **options):
        
        countrytype, _ = LocationType.objects.get_or_create(name='Country', slug='country')
        provincetype, _ = LocationType.objects.get_or_create(name='Province', slug='province')
        communetype, _ = LocationType.objects.get_or_create(name='Commune', slug='commune')
        collinetype, _ = LocationType.objects.get_or_create(name='Colline', slug='colline')
        parent_types = {
            'root_node': None,
            'Province': countrytype,
            'Commune': provincetype,
            'Colline': communetype,
            }
        
        Location.objects.all().delete()
        point, _ = Point.objects.get_or_create(latitude=3.2836, longitude=29.8293)
        loc, _ = Location.objects.get_or_create(point=point, type=countrytype, name='Burundi')
        
        path = options["path"]
        workbook = xlrd.open_workbook(path)
        worksheets = workbook.sheet_names()
        
        
        
        for worksheet_name in worksheets:
            worksheet = workbook.sheet_by_name(worksheet_name)
            num_rows = worksheet.nrows - 1
            num_cells = worksheet.ncols - 1
            curr_row = 0
            while curr_row < num_rows:
                curr_row += 1
                row = worksheet.row(curr_row)
                curr_cell = -1
                cell_content = []
                while curr_cell < num_cells:
                    curr_cell += 1
                    cell_content.append(worksheet.cell_value(curr_row, curr_cell))
                try:        
                    point, _ = Point.objects.get_or_create(\
                                    latitude=cell_content[3],\
                                    longitude=cell_content[2]\
                                )
                    location, _ = Location.objects.get_or_create(\
                                    point=point, \
                                    type=LocationType.objects.get(name=worksheet_name), \
                                    parent_id=Location.objects.get(name=cell_content[1], type=parent_types[worksheet_name]).pk, \
                                    name=cell_content[0]\
                                )
                    print 'Created: ', point, location
                except:
                    print 'There was problem creating: ', cell_content
                                                