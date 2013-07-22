#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Created on Mar 30, 2013

@author: asseym
'''
from django.test import TestCase
from django.contrib.sites.models import Site
from rapidsms.messages.incoming import IncomingMessage
from rapidsms.messages.outgoing import OutgoingMessage
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router, HttpRouter
from rapidsms.contrib.locations.models import Location, LocationType
import datetime
from rapidsms.models import Connection, Backend, Contact
from django.conf import settings
from script.models import Script, ScriptProgress, ScriptSession, ScriptStep, ScriptResponse
from rapidsms_httprouter.router import get_router
from django.core.management import call_command
from django.test.client import Client
from script.signals import script_progress_was_completed, script_progress
from script.utils.handling import find_best_response
from ureport.models.database_views import UreportContact
import difflib

class AutoRegTest(TestCase): #pragma: no cover
    fixtures = ['autoreg_data.json']
    # Model tests
    def setUp(self):
        
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 2)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'ureport.com'})

        self.backend, _ = Backend.objects.get_or_create(name='test')
        self.connection, _ = Connection.objects.get_or_create(identity='8675309', backend=self.backend)
        country = LocationType.objects.create(name='country', slug='country')
        province = LocationType.objects.create(name='province', slug='province')
        colline = LocationType.objects.create(name='colline', slug='colline')
        self.root_node = Location.objects.create(type=country, name='Burundi')
        self.bujumbura_province = Location.objects.create(type=province, name='Bujumbura Marie')
        self.kibenga_colline = Location.objects.create(type=colline, name='kibenga')
        
        settings.ROUTER_PASSWORD = None
        settings.ROUTER_URL = None

        # make celery tasks execute immediately (no redis)
        settings.CELERY_ALWAYS_EAGER = True
        settings.BROKER_BACKEND = 'memory'
        
#        router = get_router()
        
    def fake_incoming(self, message, connection=None):
        phone_number = '8675309' if connection == None else connection.identity
        c = Client()
        response = c.get(
        '/router/receive', \
        {\
          'backend' : 'test',\
          'password' : settings.ROUTER_PASSWORD,\
          'sender' : phone_number,\
          'message' : message\
          
        })

    def spoof_incoming_obj(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        return incomingmessage

    def elapseTime(self, progress, seconds):
        """
        This hack mimics the progression of time, from the perspective of a linear test case,
        by actually *subtracting* from the value that's currently stored (usually datetime.datetime.now())
        """
        progress.set_time(progress.time - datetime.timedelta(seconds=seconds))
        try:
            session = ScriptSession.objects.get(connection=progress.connection, script__slug=progress.script.slug, end_time=None)
            session.start_time = session.start_time - datetime.timedelta(seconds=seconds)
            session.save()
        except ScriptSession.DoesNotExist:
            pass
    
    def fake_script_dialog(self, script_prog, connection, responses, emit_signal=True):
        script = script_prog.script
        ss = ScriptSession.objects.create(script=script, connection=connection, start_time=datetime.datetime.now())
        for poll_name, resp in responses:
            poll = script.steps.get(poll__name=poll_name).poll
            poll.process_response(self.spoof_incoming_obj(resp, connection))
            resp = poll.responses.all()[0]
            ScriptResponse.objects.create(session=ss, response=resp)
        if emit_signal:
            script_progress_was_completed.send(connection=connection, sender=script_prog)
        return ss
    
    def register_reporter(self, join_word, grp, phone=None):
        connection = Connection.objects.create(identity=phone, backend=self.backend) if phone else self.connection
        self.fake_incoming(join_word, connection)
        script_prog = ScriptProgress.objects.all().order_by('-time')[0]

        params = [
            ('reporter_group_en', grp),\
            ('reporter_reporting_location_en', 'Bujumbura M'),\
            ('reporter_colline_en', 'Kibenga'),\
            ('reporter_name_en', 'Testy Mctesterton'),\
            ('reporter_age_en', '22'),\
            ('reporter_gender_en', 'Male'),\
        ]
        self.fake_script_dialog(script_prog, connection, params)
        
    def testBasicAutoReg(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Red Cross')
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.count(), 1)
        self.assertEquals(contact.groups.all()[0].name, 'Red Cross')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
#        self.assertEqual(UreportContact.objects.count(), 1)
        
    def testBasicAutoRegFr(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter("s'inscrire", "ccroix-rouge")
        script_prog = ScriptProgress.objects.get(connection__identity='8675309', script__slug='autoreg_fr')
        self.elapseTime(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEqual(Message.objects.order_by('-pk').filter(direction='O')[0].text.encode("utf-8"), "Bienvenue dans Ureport/Burundi, ou tu peux PARTAGER et RECEVOIR l'information sur ce qui se passe dans ta communauté, C'est GRATUIT!")
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.all()[0].name, 'Red Cross')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
        
    def testBasicAutoRegKi(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter("yingira", "redcross")
        script_prog = ScriptProgress.objects.get(connection__identity='8675309', script__slug='autoreg_ki')
        self.elapseTime(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEqual(Message.objects.order_by('-pk').filter(direction='O')[0].text.encode("utf-8"), "Kaze muri Ureport/Burundi, aho ushobora gutanga no kuronka inkuru ku bibera mu karere uherereyemwo, Ni KU BUNTU!")
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.all()[0].name, 'Red Cross')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
        
    def testBasicAutoRegScouts(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Scout')
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.count(), 1)
        self.assertEquals(contact.groups.all()[0].name, 'Scouts')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
        
    def testBasicAutoRegGuides(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Guides')
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.count(), 1)
        self.assertEquals(contact.groups.all()[0].name, 'Guides')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
        
    def testBasicAutoRegTeachers(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Teachers')
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.bujumbura_province)
        self.assertEquals(contact.colline, self.kibenga_colline)
        print contact.groups.all()
        self.assertEquals(contact.groups.count(), 1)
        self.assertEquals(contact.groups.all()[0].name, 'Teacher')
        birth_date = datetime.datetime.now() - datetime.timedelta(days=(365 * 22))
        self.assertEquals(contact.birthdate.date(), birth_date.date())
        self.assertEquals(contact.gender, 'M')
        self.assertEquals(contact.default_connection, self.connection)
               
    def testAutoregProgression(self):
        Script.objects.filter(slug='autoreg_en').update(enabled=True)
        print Script.objects.all()
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection__identity='8675309', script__slug='autoreg_en')
        self.elapseTime(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-pk')[0].text, Script.objects.get(slug='autoreg_en').steps.get(order=0).message)
        
    def testAutoregProgressionFr(self):
        Script.objects.filter(slug='autoreg_fr').update(enabled=True)
        print Script.objects.all()
        self.fake_incoming("s'inscrire")
        script_prog = ScriptProgress.objects.get(connection__identity='8675309', script__slug='autoreg_fr')
        self.elapseTime(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        from poll.models import Translation
        translated_message = Translation.objects.get(field = Script.objects.get(slug='autoreg_en').steps.get(order=0).message, language='fr')
        print translated_message
        self.assertEquals(Message.objects.filter(direction='O').order_by('-pk')[0].text, translated_message.value)
        
    def testAutoregProgressionKi(self):
        Script.objects.filter(slug='autoreg_ki').update(enabled=True)
        print Script.objects.all()
        self.fake_incoming("Injira")
        script_prog = ScriptProgress.objects.get(connection__identity='8675309', script__slug='autoreg_ki')
        self.elapseTime(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        from poll.models import Translation
        translated_message = Translation.objects.get(field = Script.objects.get(slug='autoreg_en').steps.get(order=0).message, language='ki')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-pk')[0].text, translated_message.value)
        
    def testDoubleReg(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Red Cross')
        call_command('check_script_progress', e=8, l=24)
        ScriptProgress.objects.all().delete()
        self.fake_incoming('join')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-pk')[0].text, getattr(settings,'OPTED_IN_CONFIRMATION','')['en'])
        
    def testChangeLanguage(self):
        Script.objects.all().update(enabled=True)
        self.register_reporter('join', 'Red Cross')
        self.assertEquals(Contact.objects.count(), 1)
        ScriptProgress.objects.all().delete()
        self.fake_incoming('fr')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-pk')[0].text, getattr(settings,'LANGUAGE_CHANGE_CONFIRMATION','')['fr'])