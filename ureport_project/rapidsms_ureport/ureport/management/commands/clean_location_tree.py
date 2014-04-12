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
        provincetype, _ = LocationType.objects.get_or_create(name='Province', slug='district')
        communetype, _ = LocationType.objects.get_or_create(name='Commune', slug='county')
        collinetype, _ = LocationType.objects.get_or_create(name='Colline', slug='subcounty')
        parent_types = {
            'root_node': None,
            'Province': countrytype,
            'Commune': provincetype,
            'Colline': communetype,
            }
        
        root_node = Location.tree.root_nodes()[0]
        provinces = Location.objects.filter(type__slug='district')
        for p in provinces:
            print 'found province...:%s' % p.name
            p.tree_parent = root_node
            print 'setting tree_parent to...:%s' % root_node.name
            p.save()
            print 'CHILDREN:COUNTIES for...:%s' % p.name
            counties = Location.objects.filter(parent_id=p.pk)
            for c in counties:
                print 'found county...:%s"' % c.name
                c.tree_parent = p
                print 'setting tree_parent to...:%s' % p.name
                c.save()
                print 'CHILDREN:SUBCOUNTIES for...:%s' % c.name
                subounties = Location.objects.filter(parent_id=c.pk)
                for sc in subounties:
                    print 'found subcounty...:%s"' % sc.name
                    sc.tree_parent = c
                    print 'setting tree_parent to...:%s' % sc.name
                    sc.save()

           
            


