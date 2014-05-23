from django.core.management.base import BaseCommand
from rapidsms_httprouter.models import Message
from rapidsms.log.mixin import LoggerMixin
from rapidsms.models import Connection
from django.core.files import File

class Command(BaseCommand, LoggerMixin):
    help = """contacts from old DB
    """
    def handle(self, **options):
        """

        """
        self.info("starting up")
	f = open('/tmp/messages_row_data.xls', 'w')
	myfile = File(f)
	myfile.write('Number\t Message\t Date\t Flags\t In_Response_to\t Status\t Direction\n')
	for connection in Connection.objects.all():
	    identity = connection.identity 
	    myfile.write('%s\t\n' % identity)
	    for msg in Message.objects.filter(connection=connection):
		myfile.write('\t')
	        try:
	            msg.text 
	            myfile.write('%s\t' % msg.text.encode('UTF-8'))
	        except:
	            myfile.write('\t')
		try:
		    myfile.write('%s-%s-%s %s:%s:%s\t' % (msg.date.year, msg.date.month, msg.date.day, msg.date.hour, msg.date.minute, msg.date.second))
		except:
		    myfile.write('\t')
		try:
		    myfile.write('%s\t' % msg.flags)
		except:
		    myfile.write('\t')
		try:
		    myfile.write('%s\t' % msg.in_response_to)
		except:
		    myfile.write('\t')
		try:
		    myfile.write('%s\t' % msg.status)
		except:
		    myfile.write('\t')
		try:
		    myfile.write('%s\t' % msg.direction)
		except:
		    myfile.write('\t')

		myfile.write('\n')
	
	    myfile.write('\n')
	
	myfile.close()
	f.close()
	print myfile.closed
	print f.closed

