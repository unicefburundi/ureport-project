# -*- coding: utf-8 -*-
"""A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.
"""
from rapidsms.models import Contact
from unregister.models import Blacklist
from ureport.models.models import UPoll as Poll
from django.conf import settings
from ureport.models import QuoteBox
from django.conf import settings


def has_valid_pagination_limit(settings):
    try:
        pagination_limit = settings.PAGINATION_LIMIT

        if isinstance(pagination_limit, int):
            return True
        return False
    except AttributeError:
        return False


def voices(request):
    """
    a context processor that passes the total number of ureporters to all templates.
    """
    try:
        quote = QuoteBox.objects.latest()
    except QuoteBox.DoesNotExist:
        quote = None

    user = request.user

    #The variable below will contain the numbers of ureporters in the group 
    #the user who is connected belongs to. It will contain a valid value if
    #that user has loged in the system and if it is not a superuser.
    total_ureporters_for_one_group = 0


    if user.groups.count()>0 and not user.is_superuser:
        id_of_the_group_of_this_user = user.groups.get_query_set()[0].id
        total_ureporters_for_one_group = Contact.objects.filter(groups__id=id_of_the_group_of_this_user).exclude(
            connection__identity__in=Blacklist.objects.values_list('connection__identity', flat=True)).count()

    
    context = {
        'total_ureporters': Contact.objects.exclude(
            connection__identity__in=Blacklist.objects.values_list('connection__identity', flat=True)).count(),
        'polls': Poll.objects.exclude(contacts=None, start_date=None).exclude(pk__in=[297, 296, 349, 350]).order_by(
                '-start_date'),
        'deployment_id': getattr(settings, 'DEPLOYMENT_ID', 1),
        'total_ureporters_for_one_group':total_ureporters_for_one_group,
        'quote': quote,
        'geoserver_url': getattr(settings, 'GEOSERVER_URL', None),
        'map_bounds': getattr(settings, 'OPEN_LAYERS_MAP_BOUNDS', '3226872.59281459, -496397.855648315, 3434638.20264732, -256041.778361828'),
        'show_contact_info': getattr(settings, 'SHOW_CONTACT_INFO', True)
    }

    if has_valid_pagination_limit(settings):
        context['polls'] = Poll.objects.exclude(contacts=None, start_date=None).exclude(
            pk__in=[297, 296, 349, 350]).order_by(
            '-start_date')[:settings.PAGINATION_LIMIT]
    return context
