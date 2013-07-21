from django.core.management import BaseCommand
from auth.models import Group
from rapidsms.models import Connection, Contact, Backend
from optparse import OptionParser, make_option


class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
    make_option("-f", "--file", dest="path"),

    )
    
    def handle(self,**options):
        beta_grp,_=Group.objects.get_or_create(name='Beta Testers')
        backend,_=Backend.objects.get_or_create(name='yo')
        if(options["path"]):
            file = open(options["path"])
            for line in file:
                try:
                    connection = Connection.objects.get(identity='257%s' % line)
                    contact = connection.contact
                    if not contact.groups.filter(name__icontains='Beta').exists():
                        contact.groups.add(beta_grp)
                        print 'added %s to group %s' % (contact.name, beta_grp)
                except Connection.DoesNotExist:
                    connection = Connection.objects.create(identity='257%s' % line, backend=backend)
                    connection.contact = Contact.objects.create(name='Anonymous User')
                    connection.save()
                    contact = connection.contact
                    contact.groups.add(beta_grp)
                    contact.language = 'fr'
                    contact.save()
                    print 'added %s to group %s' % (contact.name, beta_grp)