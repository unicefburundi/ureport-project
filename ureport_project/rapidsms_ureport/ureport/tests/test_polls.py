#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Created on June 30, 2013

@author: asseym
'''
from django.test import TestCase
from ureport.forms import NewPollForm
from poll.models import Poll, Translation
from auth.models import User, Group
from uganda_common.models import AccessUrls, Access
from rapidsms.contrib.locations.models import Location, LocationType
from script.models import ScriptProgress, ScriptSession, ScriptResponse
from script.signals import script_progress_was_completed
from rapidsms.models import Connection, Backend, Contact
from rapidsms_httprouter.models import Message
from ureport.models import PollAttribute, UPoll
from django.conf import settings
from ureport.tasks import start_poll
import datetime


class PollTest(TestCase):
    fixtures = ['autoreg_data.json']
    
    def setUp(self):
        user = User.objects.get(username="admin")
        user.set_password('admin')
        user.is_superuser = True
        user.is_staff = True
        user.save()
        self.backend, _ = Backend.objects.get_or_create(name='test')
        self.connection, _ = Connection.objects.get_or_create(identity='8675309', backend=self.backend)
        country = LocationType.objects.create(name='country', slug='country')
        province = LocationType.objects.create(name='province', slug='province')
        colline = LocationType.objects.create(name='colline', slug='colline')
        self.root_node = Location.objects.create(type=country, name='Burundi')
        self.bujumbura_province = Location.objects.create(type=province, name='Bujumbura Marie')
        self.kibenga_colline = Location.objects.create(type=colline, name='kibenga')
        
        url, _ = AccessUrls.objects.get_or_create(url='createpoll')
        access = Access.objects.create(user=user)
        access.groups.add(Group.objects.all()[0])
        access.allowed_locations.add(Location.objects.all()[0])
        access.allowed_urls.add(url)
        
        PollAttribute.objects.create(key="viewable", key_type="bool")
        
    def register_uReporter(self, lang=None):
        lang = lang if lang else 'fr'    
        self.connection.contact = Contact.objects.create(name='Tester')
        self.connection.save()
        contact = self.connection.contact
        contact.reporting_location = self.bujumbura_province
        contact.birthdate = datetime.datetime.now() - datetime.timedelta(days=(365 * int(30)))
        contact.gender = 'M'
        contact.colline = self.kibenga_colline
        contact.language = lang
        contact.groups.add(Group.objects.filter(name__contains='Red Cross')[0])
        contact.save()
    
    def create_poll(self, poll_type='yn', grp=None):
        login = self.client.post('/accounts/login/', {'username': 'admin', 'password': 'admin'})
        self.assertEquals(User.objects.get(username="admin").is_authenticated(), True)
        if not grp:
            grp = Group.objects.filter(name__contains='Red Cross')[0].pk
            
        values = {'type': poll_type, 
                  'response_type': 'a',
                  'name': 'test poll',
                  'question_fr':'French Question here',
                  'question_en':'English Question here',
                  'question_ki':'Kirundi Question here',
                  'default_response_fr':'French default response here',
                  'default_response_en':'English default response here',
                  'default_response_ki':'Kirundi default response here',
                  'groups': '%s' % grp,
                  'provinces': '%s' % self.bujumbura_province.pk,          
        }
        response = self.client.post('/createpoll/', values, follow=True)
        
    def fake_incoming(self, message, connection=None):
        phone_number = '8675309' if connection == None else connection.identity
        response = self.client.get(
        '/router/receive', \
        {\
          'backend' : 'test',\
          'password' : settings.ROUTER_PASSWORD,\
          'sender' : phone_number,\
          'message' : message\
          
        })
        
    def testCreatePoll(self):      
        self.create_poll()
        self.assertEquals(Poll.objects.order_by('-pk')[0].name, 'test poll')
        self.assertEquals(Translation.objects.get(field='French Question here', language='en').value, 'English Question here')
        
    def testPollSubscribers(self):
        self.register_uReporter()
        self.create_poll()
        self.assertEquals(Poll.objects.get(name='test poll').contacts.all()[0].pk, Contact.objects.filter(groups__name__contains='Red Cross')[0].pk)
        
    def testStartPoll(self):
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        start_poll(poll)
        self.assertEquals(poll.start_date.date(), datetime.datetime.now().date())
        
    def testStartPollInWebThread(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        res = self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Poll.objects.get(name='test poll').start_date.date(), datetime.datetime.now().date())
        
    def testPollQueuedMessage(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        res = self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].status, 'Q')
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].text, 'French Question here')
        
    def testPollQueuedMessageEnglish(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter(lang='en')
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        res = self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].status, 'Q')
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].text, 'English Question here')
        
    def testPollQueuedMessageKirundi(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter(lang='ki')
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        res = self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].status, 'Q')
        self.assertEquals(Message.objects.order_by('-pk').filter(direction='O', connection=self.connection)[0].text, 'Kirundi Question here')
        
    def testPollResponse(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('oui')
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection).count(), 1)
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection)[0].status, 'H')
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection)[0].application, 'poll')
        self.assertEquals(poll.responses.count(), 1)
        
    def testPollResponseYesCategory(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('oui')
        from poll.models import Category, ResponseCategory
        ureporter_response = poll.contacts.filter(name='Tester')[0].responses.order_by('-pk')[0]
        self.assertEquals(ResponseCategory.objects.filter(response=ureporter_response)[0].category.name, poll.categories.filter(name='yes')[0].name)
        
    def testPollResponseNoCategory(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('no')
        from poll.models import Category, ResponseCategory
        ureporter_response = poll.contacts.filter(name='Tester')[0].responses.order_by('-pk')[0]
        self.assertEquals(ResponseCategory.objects.filter(response=ureporter_response)[0].category.name, poll.categories.filter(name='no')[0].name)
        
    def testPollResponseUnknownCategory(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = Poll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('I dont know')
        from poll.models import Category, ResponseCategory
        ureporter_response = poll.contacts.filter(name='Tester')[0].responses.order_by('-pk')[0]
        self.assertEquals(ResponseCategory.objects.filter(response=ureporter_response)[0].category.name, poll.categories.filter(name='unknown')[0].name)
        
    def testPollResponseFreeFormPoll(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll(poll_type='t')
        poll = UPoll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('I dont know')
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection).count(), 1)
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection)[0].status, 'H')
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection)[0].text, 'I dont know')
        self.assertEquals(Message.objects.filter(direction='I', connection=self.connection)[0].application, 'poll')
        self.assertEquals(poll.responses.count(), 1)
    
    def testPollViewable(self):
        settings.START_POLLS_IN_WEB_THREAD = True
        self.register_uReporter()
        self.create_poll()
        poll = UPoll.objects.get(name='test poll')
        self.client.get('/view_poll/%s/?start=True&poll=True' % poll.pk)
        self.assertEquals(Message.objects.filter(direction='O', connection=self.connection).count(), 1)
        self.fake_incoming('I dont know')
        from poll.models import Category, ResponseCategory
        ureporter_response = poll.contacts.filter(name='Tester')[0].responses.order_by('-pk')[0]
        self.assertEquals(ResponseCategory.objects.filter(response=ureporter_response)[0].category.name, poll.categories.filter(name='unknown')[0].name)
        self.client.get('/view_poll/%s/?viewable=True&poll=True' % poll.pk)
        self.assertEquals(UPoll.objects.get(name='test poll').viewable, True)
        
    def testCreateFreeFormPoll(self):
        self.register_uReporter()      
        self.create_poll(poll_type='t')
        self.assertEquals(Poll.objects.order_by('-pk')[0].name, 'test poll')
        self.assertEquals(Poll.objects.order_by('-pk')[0].type, 't')
        self.assertEquals(Translation.objects.get(field='French Question here', language='en').value, 'English Question here')
        
    def testDeletePoll(self):
        self.register_uReporter()      
        self.create_poll(poll_type='t')
        poll = UPoll.objects.get(name='test poll')
        self.assertEquals(Poll.objects.order_by('-pk')[0].name, 'test poll')
        self.client.get('/polls/%s/delete' % poll.pk)
        self.assertEquals(Poll.objects.filter(name='test poll').count(), 0)
        
        
        