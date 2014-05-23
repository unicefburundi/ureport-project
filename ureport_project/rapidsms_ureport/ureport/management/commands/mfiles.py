from django.core.management.base import BaseCommand

from rapidsms.log.mixin import LoggerMixin
from rapidsms.models import Connection, Contact
from rapidsms.contrib.location.models import Location
from django.core.files import File

class Command(BaseCommand, LoggerMixin):
    help = """Migrate contacts from DB to excel file"""
    def handle(self, **options):
        """

        """
        self.info("starting up")
	f = open('/tmp/row_data.xls', 'w')
	myfile = File(f)
	myfile.write('Number\t Network\t Name\t Active\t Birthdate\t Province\t Colline_id\t Colline_name\t Commune_id\t Commune_name\t Created_on\t Gender\t Groups\t Language\n')
	for connection in Connection.objects.all():
	    identity = connection.identity 
	    myfile.write('%s\t' % identity)
	    try:
	       backend =  connection.backend.name
	       myfile.write('%s\t' % backend)
	    except:
	       myfile.write('None\t')
	    try:
		contact = connection.contact
	    	try:
		    myfile.write('%s\t' % connection.contact.name.encode('UTF-8'))
	        except:
		    myfile.write('None\t')
		try:    
		    myfile.write('%s\t' % contact.active)
		except:
		    myfile.write('None\t')
		try:
		    myfile.write('%s-%s-%s\t' % (contact.birthdate.year, contact.birthdate.month, contact.birthdate.day))
		except:
		    myfile.write('None\t')
		try:
		    myfile.write('%s\t' % contact.reporting_location.name.encode('UTF-8'))
		except:
		    myfile.write('None\t')
		try:
		    myfile.write('%s\t' % contact.colline_id)
		    myfile.write('%s\t' % Location.objects.get(pk=contact.colline_id).name.encode('UTF-8'))
		except:
		    myfile.write('None\t')
		try:
		    myfile.write('%s\t' % contact.commune_id)
		    myfile.write('%s\t' % Location.objects.get(pk=contact.commune_id).name.encode('UTF-8'))
		except:
		    myfile.write('None\t')
		try:    
		    myfile.write('%s\t' % contact.created_on)
	        except:
		    myfile.write('None\t')
		try:    
		    myfile.write('%s\t' % contact.gender)
                except:
		    myfile.write('None\t')
		try:
		    for g in contact.groups.all():
		    	myfile.write('%s-' % g.name.encode('UTF-8'))
		    myfile.write('\t')
		except:
		    myfile.write('None\t')
		try:
		    myfile.write('%s\t' % contact.language.encode('UTF-8'))
		except:
		    myfile.write('None\t')
	    except:
		contact = 'No Contact'
	
	    myfile.write('\n')
	
	myfile.close()
	f.close()
	print myfile.closed
	print f.closed

