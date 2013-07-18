#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from ureport.models import AutoregGroupRules
from script.models import *
from eav.models import Attribute
from poll.models import Category, Rule
from poll.models import Translation
import re

def init_structures():
    if 'django.contrib.sites' in settings.INSTALLED_APPS:
        site_id = getattr(settings, 'SITE_ID', 1)
        site = Site.objects.get_or_create(pk=site_id, defaults={'domain':'ureport.unicefburundi.org'})
        Poll.objects.all().delete()
        init_groups()
        init_eav_attributes(site[0])
        init_scripts(site[0])

def init_groups():
    groups = {
        'Red Cross': 'Red Cross,Redcross,Croix-Rouge,Croix Rouge',
        'Scouts': 'Scouts',
        'Guides': 'Guides',
        'Other Reporters': 'Other Reporters',
    }
    for g, aliases in groups.items():
        grp, _ = Group.objects.get_or_create(name=g)
        AutoregGroupRules.objects.get_or_create(group=grp, values=aliases)
        
        
def init_eav_attributes(site):
    if 'django.contrib.sites' in settings.INSTALLED_APPS:
#        site_id = getattr(settings, 'SITE_ID', 1)

#        site, created = Site.objects.get_or_create(pk=site_id, defaults={'domain':'ureport.unicefburundi.org'})
        eav_text_value = Attribute.objects.get_or_create(slug='poll_text_value', datatype=Attribute.TYPE_TEXT, site=Site.objects.get(id=site.id))
        eav_number_value = Attribute.objects.get_or_create(slug='poll_number_value', datatype=Attribute.TYPE_FLOAT, site=Site.objects.get(id=site.id))
        eav_location_value = Attribute.objects.get_or_create(slug='poll_location_value', datatype=Attribute.TYPE_OBJECT, site=Site.objects.get(id=site.id))
                
def init_scripts(site):
    #Message, Text, Rule, Start Offset, 'Retry Offset, Give up Offset, Number of Tries, 
    simple_scripts = {
        #English autoreg
	    'autoreg en':[     (False, "Welcome to Ureport Burundi, where you can SHARE and RECEIVE information about what is happening in your community. It’s FREE!", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_group', "Please type the name of your organization/group ONLY", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_LOCATION, 'reporter_reporting_location', "Tell us where you’ll be reporting from so we can work together to try to resolve issues in your community. Reply with the name of your province ONLY", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_LOCATION, 'reporter_colline', "From which colline will you be reporting? Please respond ONLY with the name of your colline.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (False, "UReport is a FREE text messaging service sponsored by UNICEF and other partners.", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_name', "What is your name? Your name will not be revealed without your permission and you can use a nickname.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_NUMERIC, 'reporter_age', "What is your age?", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_TEXT, 'reporter_gender', "Are you male or female? Type F for 'female' and M for 'male'", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0, {"male":["m", "mal", "male", "ma", "mas", "masculin", "umugabo", "ga", "gabo", "gab"], "female": ["f", "fem", "female", "fe", "fém" "féminin", "fé", "umugore", "gore", "go", "gor"]}),
                           (False, "CONGRATULATIONS!! You are now  registered as a UReporter! Make a real difference with Ureport Burundi, Speak up and be heard! From UNICEF", ScriptStep.WAIT_MOVEON, 0, False, False, 0,),
                     ],
        }
    script_translations = {
        #French autoreg
        'autoreg fr':[     (False, "Bienvenue à Ureport Burundi, ou tu peux PARTAGER et RECEVOIR des informations sur ce qui se posse dans ta communauté.  C’est GRATUIT !", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_group', "Appartiens-tu à une Organisation de volontaires? S'il te plaît réponds par le nom de l'organisation SEULEMENT", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_LOCATION, 'reporter_reporting_location', "Dis-nous d'où tu rapportes afin que nous puissions travailler ensemble pour résoudre les défis de ta communauté ! Réponds avec le nom de ta province !", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_LOCATION, 'reporter_colline', "De quelle colline rapporteras-tu ? S’il te plaît réponds SEULEMENT avec le nom de ta colline", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (False, "UReport est un service GRATUIT de messagerie sponsorisée par l'UNICEF et d'autres partenaires.", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_name', "Comment t’appelles-tu ? Ton nom ne sera pas révélé sans ta permission et tu peux utiliser un surnom.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_NUMERIC, 'reporter_age', "Quel âge as –tu ?", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_TEXT, 'reporter_gender', "Es-tu de sexe masculin ou féminin? Écris F pour féminin et M pour masculin", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0, {"male":["m", "mas", "masculin", "ma"], "female": ["f", "fem", "fém" "féminin", "fé"]}),
                           (False, "Félicitations ! Tu es maintenant enregistré Ureporter. Fais une vraie différence avec Ureport Burundi ! Parles et sois écouté ! De l’UNICEF", ScriptStep.WAIT_MOVEON, 0, False, False, 0,),
                     ],
        #Kirundi autoreg
        'autoreg ki':[     (False, "Kaze muri Ureport/Burundi, aho ushobora gutanga no kuronka inkuru ku bibera mu karere uherereyemwo, Ni KU BUNTU!", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_group', "Woba uri umunywanyi mw'ishirahamwe ry'abitanga? Ishura n'izina ry'iryo Shirahamwe GUSA.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_LOCATION, 'reporter_reporting_location', "Tubwire akarere utangiramwo inkuru, bidufashe gukorera hamwe gutorera inyishu ingorane zo mu karere kanyu! Ishura izina ry'intara yawe GUSA", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_LOCATION, 'reporter_colline', "Ni uwuhe mutumba utangiramwo inkuru? Ishura izina ry'umutumba wawe GUSA.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (False, "Ureport Ni uburyo bwo kurungika ubutumwa ku buntu, bifashijwe n'intererano ya UNICEF n'ayandi mashiramwe.", ScriptStep.WAIT_MOVEON, 0, False, 60, 0,),
                           (Poll.TYPE_TEXT, 'reporter_name', "Tanga izina ryawe, ibikuranga bifasha guha insiguro inkuru turonse. Izina ryawe ntituritanga utaduhaye uruhusha kandi ushobora gutanga amatazirano", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0,),
                           (Poll.TYPE_NUMERIC, 'reporter_age', "Ufise imyaka ingahe?", ScriptStep.STRICT_MOVEON, 0, 3600, 3600, 3,),
                           (Poll.TYPE_TEXT, 'reporter_gender', "Woba uri uw'igitsina Gore canke igitsina Gabo? Andika Go ari igitsina Gore Na Ga ari igitsina Gabo.", ScriptStep.WAIT_MOVEON, 0, False, 3600, 0, {"male":["umugabo", "ga", "gabo", "gab"], "female": ["umugore", "gore", "go", "gor"]}),
                           (False, "MURAKOZE!! Ubu uri umunywanyi WA Ureport. Gira ico uhinduye c'ukuri hamwe Na UReport Burundi. Vuga hama wumvirizwe! Kubwa UNICEF.", ScriptStep.WAIT_MOVEON, 0, False, False, 0,),
                     ],
    }

    user = User.objects.get_or_create(username='admin')[0]

    for script_name, polls in simple_scripts.items():
#        Script.objects.filter(slug="%s"%script_name.lower().replace(' ', '_')).delete()
        #We are trying to not recreate scripts in order to not mess up people who have active sessions attached to scripts
        script, created = Script.objects.get_or_create(slug="%s" % script_name.lower().replace(' ', '_'))
        script.name = "Ureport %s script" % script_name
        script.save()
        scriptname_parts = script_name.split(' ')
#        import ipdb;ipdb.set_trace()
        #If its a new script we are adding
        if created:
            script.sites.add(Site.objects.get_current())
            
            step = 0
            for poll_info in polls:
                if poll_info[0]:
                    Poll.objects.filter(name=poll_info[1]).delete()
                    poll = Poll.objects.create(user=user, type=poll_info[0], name='%s_%s'%(poll_info[1], scriptname_parts[1]), default_response='', question=poll_info[2])
                    poll.sites.add(Site.objects.get_current())
                    poll.save()
                    
                    if len(poll_info) > 8 and poll_info[8]:
                        for cat, rules in poll_info[8].items():
                            category, _ = Category.objects.get_or_create(name=cat, poll=poll)
                            regex = '%s%s%s'% ('^\s*(', '|'.join(rules), ')(\s|[^a-zA-Z]|$)')
                            rule, _ = Rule.objects.get_or_create(regex=regex, category=category, rule_type='r', rule_string='|'.join(rules))
                    if len(poll_info) > 9 and poll_info[9]:
                        poll.add_yesno_categories()
                    
                    script.steps.add(\
                                ScriptStep.objects.get_or_create(
                                script=script,
                                poll=poll,
                                order=step,
                                rule=poll_info[3],
                                start_offset=poll_info[4],
                                retry_offset=poll_info[5],
                                giveup_offset=poll_info[6],
                                num_tries=poll_info[7],
                        )[0])
                else:
                    script.steps.add(\
                                ScriptStep.objects.get_or_create(
                                script=script,
                                message=poll_info[1],
                                order=step,
                                rule=poll_info[2],
                                start_offset=poll_info[3],
                                retry_offset=poll_info[4],
                                giveup_offset=poll_info[5],
                                num_tries=poll_info[6],
                        )[0])
                step = step + 1
        
        #This is an old script, we can simply attempt to update its steps and poll information
        else:
            step = 0
            script_step = script.steps.get(order=step, script__slug=script.slug)
            for poll_info in polls:
                if poll_info[0]:
                    #We can delete the poll and recreate it, doesn't matter the poll a step is attached to is traced by the step not Poll ID
                    Poll.objects.filter(name=poll_info[1]).delete()
                    poll = Poll.objects.create(user=user, type=poll_info[0], name='%s_%s'%(poll_info[1], scriptname_parts[1]), default_response='', question=poll_info[2])
                    poll.sites.add(Site.objects.get_current())
                    poll.save()
                    
                    if len(poll_info) > 8 and poll_info[8]:
                        for cat, rules in poll_info[8].items():
                            category, _ = Category.objects.get_or_create(name=cat, poll=poll)
                            regex = '%s%s%s'% ('^\s*(', '|'.join(rules), ')(\s|[^a-zA-Z]|$)')
                            rule, _ = Rule.objects.get_or_create(regex=regex, category=category, rule_type='r', rule_string='|'.join(rules))
                    if len(poll_info) > 9 and poll_info[9]:
                        poll.add_yesno_categories()
                        
                    script_step.poll = poll
                    script_step.order = step #Order might change due to insertion or deletion of steps
                    script_step.rule = poll_info[3]
                    script_step.start_offset=poll_info[4]
                    script_step.retry_offset=poll_info[5]
                    script_step.giveup_offset=poll_info[6]
                    script_step.num_tries=poll_info[7]
                    script_step.save()
                else:
                    script_step.message = poll_info[1]
                    script_step.order = step
                    script_step.rule = poll_info[2]
                    script_step.start_offset=poll_info[3]
                    script_step.retry_offset=poll_info[4]
                    script_step.giveup_offset=poll_info[5]
                    script_step.num_tries=poll_info[6]
                    script_step.save()
                step = step + 1
                
    for script_name, polls in script_translations.items():
        #Even for translated scripts, we try not to unnecessarily recreate scripts
        script, created = Script.objects.get_or_create(slug="%s" % script_name.lower().replace(' ', '_'))
        script.name = "Ureport %s script" % script_name
        script.save()
        scriptname_parts = script_name.split(' ')
        #If NEW translation, create new steps based on the English script. Since its merely a translation, we assume scripts are identical in structure
        if created:
            script.sites.add(Site.objects.get_current())
            for en_step in ScriptStep.objects.filter(script__slug='autoreg_en'):
                if en_step.message:
                    script.steps.add(ScriptStep.objects.get_or_create(
                                    script=script,
                                    message=en_step.message,
                                    order=en_step.order,
                                    rule=en_step.rule,
                                    start_offset=en_step.start_offset,
                                    retry_offset=en_step.retry_offset,
                                    giveup_offset=en_step.giveup_offset,
                                    num_tries=en_step.num_tries,
                            )[0]
                        )
                else:
                    script.steps.add(ScriptStep.objects.get_or_create(
                                    script=script,
                                    poll=en_step.poll,
                                    order=en_step.order,
                                    rule=en_step.rule,
                                    start_offset=en_step.start_offset,
                                    retry_offset=en_step.retry_offset,
                                    giveup_offset=en_step.giveup_offset,
                                    num_tries=en_step.num_tries,
                            )[0]
                        )
            #And finally the translations for the steps
            step = 0
            for poll_info in polls:
                if poll_info[0]:
                    translation, _ = Translation.objects.get_or_create(language=scriptname_parts[1], \
                                                field=Poll.objects.get(name='%s_en'% poll_info[1]).question, \
                                                value=poll_info[2])
                else:
                    translation, _ = Translation.objects.get_or_create(language=scriptname_parts[1], \
                                                field=ScriptStep.objects.get(script__slug='autoreg_en', order=step).message, \
                                                value=poll_info[1])
                step = step + 1
                
        #Its an old script, but steps could have changed
        else:
            for en_step in ScriptStep.objects.order_by('order').filter(script__slug='autoreg_en'):
                try:
                    script_step = script.steps.get(order=en_step.order, script__slug=script.slug)
                    if en_step.message:
                        script_step.message = en_step.message
                    else:
                        script_step.poll = en_step.poll
                    script_step.order = en_step.order, #we might need to maintain the integrity scriptprogress by preserving step.order but the english script might have added a new step, what happens?
                    script_step.rule = en_step.rule
                    script_step.start_offset = en_step.start_offset
                    script_step.retry_offset = en_step.retry_offset
                    script_step.giveup_offset = en_step.giveup_offset
                    script_step.num_tries = en_step.num_tries
                    script_step.save()
                    
                #It is possible that a new step was added so, we add the step
                except ScriptStep.DoesNotExist:
                    if en_step.message:
                        script.steps.add(ScriptStep.objects.get_or_create(
                                    script=script,
                                    message=en_step.message,
                                    order=en_step.order,
                                    rule=en_step.rule,
                                    start_offset=en_step.start_offset,
                                    retry_offset=en_step.retry_offset,
                                    giveup_offset=en_step.giveup_offset,
                                    num_tries=en_step.num_tries,
                            )[0]
                        )
                    else:
                        script.steps.add(ScriptStep.objects.get_or_create(
                                    script=script,
                                    poll=en_step.poll,
                                    order=en_step.order,
                                    rule=en_step.rule,
                                    start_offset=en_step.start_offset,
                                    retry_offset=en_step.retry_offset,
                                    giveup_offset=en_step.giveup_offset,
                                    num_tries=en_step.num_tries,
                            )[0]
                        )
                        
            #Translation can always change, no biggy              
            step = 0
            for poll_info in polls:
                if poll_info[0]:
                    translation, _ = Translation.objects.get_or_create(language=scriptname_parts[1], \
                                                field=Poll.objects.get(name='%s_en'% poll_info[1]).question, \
                                                value=poll_info[2])
                else:
                    translation, _ = Translation.objects.get_or_create(language=scriptname_parts[1], \
                                                field=ScriptStep.objects.get(script__slug='autoreg_en', order=step).message, \
                                                value=poll_info[1])
                step = step + 1