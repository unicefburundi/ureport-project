#!/usr/bin/python
# -*- coding: utf-8 -*-

from django import forms
from django.forms.util import ErrorList
from rapidsms.models import Contact
from django.contrib.auth.models import Group
from poll.models import Poll, Response
from mptt.forms import TreeNodeChoiceField
from generic.forms import ActionForm, FilterForm, ModuleForm
from django.conf import settings
from django.contrib.sites.models import Site
from django.forms.widgets import RadioSelect
from rapidsms.contrib.locations.models import Location
from django.forms import ValidationError
from django.db.models import Q
import re
from poll.forms import NewPollForm
from rapidsms_httprouter.models import Message, Connection
from uganda_common.forms import SMSInput
from django.db.models.query import QuerySet
from poll.models import Translation
from unregister.models import Blacklist
from .models import AutoregGroupRules
from uganda_common.utils import ExcelResponse, ExcelResults
from ureport.models import MessageAttribute, MessageDetail
from django.utils.safestring import mark_safe
from uganda_common.models import Access
import tasks
from ureport.utils import normalize_query
languages = getattr(settings, 'LANGUAGES', (('fr', 'French')))
from ureport.models import UreportContact
from django.utils.translation import ugettext as _


class EditReporterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EditReporterForm, self).__init__(*args, **kwargs)
        self.fields['reporting_location'] = \
            TreeNodeChoiceField(queryset=self.fields['reporting_location'
            ].queryset.filter(type="district"), level_indicator=u'')

    class Meta:
        model = Contact
        fields = ('name', 'reporting_location', 'groups', 'gender', 'birthdate')


class PollModuleForm(ModuleForm):
    viz_type = forms.ChoiceField(choices=(
        ('ureport.views.show_timeseries', 'Poll responses vs time'),
        ('ureport.views.mapmodule', 'Map'),
        ('histogram', 'Histogram'),
        ('ureport.views.piegraph_module', 'Pie chart'),
        ('ureport.views.tag_cloud', 'Tag cloud'),
        ('poll-responses-module', 'Responses list'),
        ('poll-report-module', 'Tabular report'),
        ('best-viz', 'Results'),
        ('ureport.views.message_feed', 'Message Feed'),
    ), label='Poll visualization')
    poll = forms.ChoiceField(choices=(('l', 'Latest Poll'), )
                                     + tuple([(int(p.pk), str(p)) for p in
                                              Poll.objects.all().order_by('-start_date'
                                              )]), required=True)

    def setModuleParams(
            self,
            dashboard,
            module=None,
            title=None,
    ):
        title_dict = {
            'ureport.views.show_timeseries': 'Poll responses vs time',
            'ureport.views.mapmodule': 'Map',
            'histogram': 'Histogram',
            'ureport.views.piegraph_module': 'Pie chart',
            'ureport.views.tag_cloud': 'Tag cloud',
            'poll-responses-module': 'Responses list',
            'poll-report-module': 'Tabular report',
            'best-viz': 'Results',
            'ureport.views.message_feed': 'Message Feed',
        }
        viz_type = self.cleaned_data['viz_type']
        title = title_dict[viz_type]
        module = module or self.createModule(dashboard, viz_type,
                                             title=title)
        is_url_param = viz_type in ['poll-responses-module',
                                    'poll-report-module']
        if is_url_param:
            param_name = 'poll_id'
        else:
            param_name = 'pks'
        param_value = str(self.cleaned_data['poll'])
        module.params.create(module=module, param_name=param_name,
                             param_value=param_value,
                             is_url_param=is_url_param)
        return module


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='Contacts Excel File',
                                 required=False)
    assign_to_group = \
        forms.ModelChoiceField(queryset=Group.objects.all(),
                               required=False)

    #    def __init__(self, data=None, **kwargs):
    #        self.request=kwargs.pop('request')
    #        if data:
    #            forms.Form.__init__(self, data, **kwargs)
    #        else:
    #            forms.Form.__init__(self, **kwargs)
    #        if hasattr(Contact, 'groups'):
    #            if self.request.user.is_authenticated():
    #                self.fields['assign_to_group'] = forms.ModelChoiceField(queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk',flat=True)), required=False)
    #            else:
    #                self.fields['assign_to_group'] = forms.ModelChoiceField(queryset=Group.objects.all(), required=False)

    def clean(self):
        excel = self.cleaned_data.get('excel_file', None)
        if excel and excel.name.rsplit('.')[1] != 'xls':
            msg = u'Upload valid excel file !!!'
            self._errors['excel_file'] = ErrorList([msg])
            return ''
        return self.cleaned_data


class ExcelTestUploadForm(forms.Form):
    excel_file = forms.FileField(label='Contacts Excel File',
                                required=False,
                                help_text='Upload an excel file of 200 rows maximum')

    def good_file(self):
        excel = self.cleaned_data.get('excel_file', None)
        if excel and excel.name.rsplit('.')[-1] != 'xlsx' and excel.name.rsplit('.')[-1] != 'xlt':
            msg = u'Upload valid excel file !!!'
            self._errors['excel_file'] = ErrorList([msg])
            return ''
        return self.cleaned_data


class SearchResponsesForm(FilterForm):
    """ search responses
    """

    search = forms.CharField(max_length=100, required=True,
                             label='search Responses')

    def filter(self, request, queryset):
        search = self.cleaned_data['search'].strip()
        if search == '':
            return queryset

        elif search[0] == "'" and search[-1] == "'":

            search = search[1:-1]
            return queryset.filter(Q(message__text__iexact=search)
                                   | Q(message__connection__contact__reporting_location__name__iexact=search)
                                   | Q(message__connection__pk__iexact=search))
        elif search == "=numerical value()":
            return queryset.filter(message__text__iregex="(-?\d+(\.\d+)?)")
        else:

            return queryset.filter(Q(message__text__icontains=search)
                                   | Q(message__connection__contact__reporting_location__name__icontains=search)
                                   | Q(message__connection__pk__icontains=search))


class SearchMessagesForm(FilterForm):
    """ search messages
    """

    search = forms.CharField(max_length=100, required=True,
                             label='search ')

    def filter(self, request, queryset):

        search = self.cleaned_data['search'].strip()
        if search == '':
            return queryset
        elif search[0] == '"' and search[-1] == '"':
            search = search[1:-1]
            return queryset.filter(Q(text__iregex=".*\m(%s)\y.*"
                                                  % search)
                                   | Q(connection__contact__reporting_location__name__iregex=".*\m(%s)\y.*"
                                                                                             % search)
                                   | Q(connection__pk__iregex=".*\m(%s)\y.*"
                                                              % search))

        elif search == "'=numerical value()'":
            return queryset.filter(text__iregex="^[0-9]+$")

        elif search[0] == "'" and search[-1] == "'":

            search = search[1:-1]
            return queryset.filter(Q(text__iexact=search)
                                   | Q(connection__contact__reporting_location__name__iexact=search)
                                   | Q(connection__pk__iexact=search))
        elif search == "=numerical value()":
            return queryset.filter(text__iregex="(-?\d+(\.\d+)?)")
        else:

            return queryset.filter(Q(text__icontains=search)
                                   | Q(connection__contact__reporting_location__name__icontains=search)
                                   | Q(connection__pk__icontains=search))


class AssignToPollForm(ActionForm):
    """ assigns responses to poll  """

    poll = \
        forms.ModelChoiceField(queryset=Poll.objects.all().order_by('-pk'
        ))
    action_label = 'Assign selected to poll'

    def perform(self, request, results):
        poll = self.cleaned_data['poll']
        for c in results:
            c.categories.all().delete()
            c.poll = poll
            c.save()
        return ('%d responses assigned to  %s poll' % (len(results),
                                                       poll.name), 'success')


class DeleteSelectedForm(ActionForm):
    """ Deletes selected stuff  """

    action_label = 'Delete Selected '
    action_class = 'delete'

    def perform(self, request, results):
        count = len(results)
        if not count:
            return ('No contacts selected', 'error')

        if isinstance(results[0], QuerySet):
            results.delete()
        else:
            for object in results:
                object.delete()

        return ('%d  objects successfuly deleted ' % count, 'success')


class AssignToNewPollForm(ActionForm):
    """ assigns contacts to poll"""

    action_label = 'Assign to New poll'
    poll_name = forms.CharField(label='Poll Name', max_length='100')
    POLL_TYPES = [('yn', 'Yes/No Question')] + [(c['type'], c['label']) for c in Poll.TYPE_CHOICES.values()]
    response_type = forms.ChoiceField(choices=Poll.RESPONSE_TYPE_CHOICES, widget=RadioSelect)
    poll_type = forms.ChoiceField(choices=POLL_TYPES)

    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        i = 0
        for lang, lang_verbose in languages:
            form_name = 'question_%s' % lang
            if i == 0:
                self.fields[form_name] = forms.CharField(label=lang_verbose, max_length=160, required=True, widget=SMSInput())
            else:
                self.fields[form_name]  = forms.CharField(label=lang_verbose, max_length=160, required=False, widget=SMSInput())
            i +=1
    default_response = forms.CharField(max_length=160, required=False,widget=SMSInput())


    def perform(self, request, results):
        #TODO: Deal with languages
        languages = ["fr"]
        question_fr = self.cleaned_data.get('question_fr', "")
        question_fr = question_fr.replace('%', u'\u0025')

        if not self.cleaned_data['question_en'] == '':
            languages.append('en')
            (translation, created) = \
                Translation.objects.get_or_create(language='en',
                    field=self.cleaned_data['question_fr'],
                    value=self.cleaned_data['question_en'])

        if not self.cleaned_data['question_ki'] == '':
            languages.append('ki')
            (translation, created) = \
                Translation.objects.get_or_create(language='ki',
                    field=self.cleaned_data['question_fr'],
                    value=self.cleaned_data['question_ki'])

        if not len(results):
            return ('No contacts selected', 'error')
        name = self.cleaned_data['poll_name']
        poll_type = self.cleaned_data['poll_type']
        poll_type = self.cleaned_data['poll_type']
        if poll_type == NewPollForm.TYPE_YES_NO:
            poll_type = Poll.TYPE_TEXT

#        question = self.cleaned_data.get('question').replace('%', u'\u0025')
        default_response = self.cleaned_data['default_response']
        response_type = self.cleaned_data['response_type']
        contacts = Contact.objects.filter(pk__in=results)
        poll = Poll.create_with_bulk(
            name=name,
            type=poll_type,
            question=question_fr,
            default_response=default_response,
            contacts=contacts,
            user=request.user
        )

        poll.response_type = response_type
        if self.cleaned_data['poll_type'] == NewPollForm.TYPE_YES_NO:
            poll.add_yesno_categories()
        poll.save()

        if settings.SITE_ID:
            poll.sites.add(Site.objects.get_current())

        return ('%d participants added to  %s poll' % (len(results),
                                                       poll.name), 'success')


DISTRICT_CHOICES = tuple([(int(d.pk), d.name) for d in
                          Location.objects.filter(type__slug='district'
                          ).order_by('name')])
phone_re = re.compile(r'(\d+)')


class SignupForm(forms.Form):
    firstname = forms.CharField(max_length=100, label='First Name')
    lastname = forms.CharField(max_length=100, label='Last Name')
    district = forms.ChoiceField(choices=DISTRICT_CHOICES,
                                 label='District')
    village = forms.CharField(label='Village', required=False)
    mobile = forms.CharField(label='Mobile Number', max_length=13,
                             required=True)
    gender = forms.ChoiceField(choices=(('M', 'Male'), ('F',
                                                        'Female')), label='Sex')
    group = forms.CharField(max_length=100, required=False,
                            label='How did you hear about U-report?')
    age = forms.IntegerField(max_value=100, min_value=10,
                             required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        cleaned_data['district'] = \
            Location.objects.get(pk=int(cleaned_data.get('district', '1'
            )))
        match = re.match(phone_re, cleaned_data.get('mobile', ''))
        if not match:
            raise ValidationError('invalid Number')
        return cleaned_data


class ReplyTextForm(ActionForm):
    text = forms.CharField(required=True, widget=SMSInput())
    action_label = 'Reply to selected'

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!',
                    'error')

        if request.user and request.user.has_perm('contact.can_message'
        ):
            text = self.cleaned_data['text']
            if isinstance(results[0], Message):
                connections = results.values_list('connection',
                                                  flat=True)
            elif isinstance(results[0], Response):
                connections = results.values_list('message__connection'
                    , flat=True)

            Message.mass_text(text,
                              Connection.objects.filter(pk__in=connections).distinct(),
                              status='P')

            return ('%d messages sent successfully' % results.count(),
                    'success')
        else:
            return ("You don't have permission to send messages!",
                    'error')

class MassTextForm(ActionForm):

    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

        i = 0
        for lang, lang_verbose in languages:
            form_name = 'text_%s' % lang
            if i == 0:
                self.fields[form_name] = forms.CharField(label=lang_verbose, max_length=160, required=True, widget=SMSInput())
            else:
                self.fields[form_name]  = forms.CharField(label=lang_verbose, max_length=160, required=False, widget=SMSInput())
            i +=1

    action_label = 'Send Message'

    def perform(self, request, results):
        from poll.models import gettext_db
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('contact.can_message'):
            blacklists = Blacklist.objects.values_list('connection')

            #TODO: Revise for proper internationalization
            languages = ["fr"]
            text_fr = self.cleaned_data.get('text_fr', "")
            text_fr = text_fr.replace('%', u'\u0025')

            if not self.cleaned_data['text_en'] == '':
                languages.append('en')
                (translation, created) = \
                    Translation.objects.get_or_create(language='en',
                        field=self.cleaned_data['text_fr'],
                        value=self.cleaned_data['text_en'])

            if not self.cleaned_data['text_ki'] == '':
                languages.append('ki')
                (translation, created) = \
                    Translation.objects.get_or_create(language='ki',
                        field=self.cleaned_data['text_fr'],
                        value=self.cleaned_data['text_ki'])

            #Everyone gets a message in their language. This behavior may not be ideal
            #since one may wish to send out a non translated message to everyone regardless of language
            #TODO: allow sending of non translated message to everyone using a flag
            total_connections = []
            for language in languages:
                connections = Connection.objects.filter(contact__in=results.filter(language=language)).exclude(pk__in=blacklists).distinct()
                messages = Message.mass_text(gettext_db(field=text_fr, language=language), connections)
                contacts = Contact.objects.filter(pk__in=results)

                total_connections.extend(connections)
            #Bulk wont work because of a ManyToMany relationship to Contact on MassText
            #Django API does not allow bulk_create() to work with relation to multiple tables
            #TODO: Find work around
#            bulk_list = [
#                     MassText(user=request.user),
#                     MassText(text=text_fr),
#                     MassText(contacts=list(contacts))
#                     ]
#            masstext = MassText.objects.bulk_create(bulk_list)

            #The bulk_insert manager needs to be updated
            #TODO: investigate changes made in new Django that are not compatible with BulkInsertManager()
#            MassText.bulk.bulk_insert(send_pre_save=False,
#                    user=request.user,
#                    text=text_fr,
#                    contacts=list(contacts))
#            masstexts = MassText.bulk.bulk_insert_commit(send_post_save=False, autoclobber=True)
#            masstext = masstexts[0]

            return ('Message successfully sent to %d numbers' % len(total_connections), 'success',)
        else:
            return ("You don't have permission to send messages!", 'error',)


class NewPollForm(forms.Form): # pragma: no cover

    TYPE_YES_NO = 'yn'
    TYPE_CHOICES = [(TYPE_YES_NO, 'Yes/No Question')]
    TYPE_CHOICES += [(choice['type'], choice['label']) for choice in Poll.TYPE_CHOICES.values()]

    print tuple(TYPE_CHOICES)

    type = forms.ChoiceField(
        required=True,
        choices=tuple(TYPE_CHOICES)
        )
    response_type = forms.ChoiceField(choices=Poll.RESPONSE_TYPE_CHOICES, widget=RadioSelect,
                                      initial=Poll.RESPONSE_TYPE_ALL)

    def updateTypes(self):
        self.fields['type'].widget.choices += [(choice['type'], choice['label']) for choice in
                                               Poll.TYPE_CHOICES.values()]

    name = forms.CharField(max_length=32, required=True)

    def __init__(self, data=None, **kwargs):
        if 'request' in kwargs:
            request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

        #Question forms
        i = 0
        for lang, lang_verbose in languages:
            form_name = 'question_%s' % lang
            form_label = 'Question:%s' % lang_verbose
            if i == 0:
                self.fields[form_name] = forms.CharField(label=form_label, max_length=160, required=True, widget=SMSInput())
            else:
                self.fields[form_name]  = forms.CharField(label=form_label, max_length=160, required=False, widget=SMSInput())
            i +=1
        #Response forms
        for lang, lang_verbose in languages:
            form_name = 'default_response_%s' % lang
            form_label = 'Default Response:%s' % lang_verbose
            self.fields[form_name]  = forms.CharField(label=form_label, max_length=160, required=False, widget=SMSInput())

        # This may seem like a hack, but this allows time for the Contact model
        # to optionally have groups (i.e., poll doesn't explicitly depend on the rapidsms-auth
        # app.
        queryset = Group.objects.order_by('name')
        if 'request' in kwargs:
            request = kwargs.pop('request')
        try:
            access = Access.objects.get(user=request.user)
            queryset = access.groups.order_by('name')
        except Access.DoesNotExist:
            pass
        except UnboundLocalError:
            pass
        if hasattr(Contact, 'groups'):
            GROUP_CHOICES = [(-1, _('Without Group'))]
            GROUP_CHOICES += [(id, name) for id, name in queryset.values_list('id', 'name')]
#             self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=queryset, required=False)
            self.fields['groups'] = forms.MultipleChoiceField(choices=GROUP_CHOICES, required=False)

    provinces = forms.ModelMultipleChoiceField(queryset=
                                               Location.objects.filter(type__slug='district'
                                               ).order_by('name'), required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        groups = cleaned_data.get('groups')
        if cleaned_data.get('question_fr', None):
            cleaned_data['question_fr'] = cleaned_data.get('question_fr').replace('%', u'\u0025')
        if cleaned_data.get('default_response_fr', None):
            cleaned_data['default_response_fr'] = cleaned_data['default_response_fr'].replace('%', u'\u0025')

        if not groups:
            raise forms.ValidationError("You must provide a set of recipients (a group or groups)")

        return cleaned_data

    def clean_default_response_fr(self):
        return self._cleaned_default_response(self.data['default_response_fr'])

    def clean_default_response_en(self):
        return self._cleaned_default_response(self.data['default_response_en'])

    def clean_default_response_ki(self):
        return self._cleaned_default_response(self.cleaned_data['default_response_ki'])

    def _cleaned_default_response(self, default_response):
        return default_response.replace('%', '%%')


class AssignResponseGroupForm(ActionForm):
    action_label = 'Assign to group(s)'

    # This may seem like a hack, but this allows time for the Contact model's
    # default manage to be replaced at run-time.  There are many applications
    # for that, such as filtering contacts by site_id (as is done in the
    # authsites app, see github.com/daveycrockett/authsites).
    # This does, however, also make the polling app independent of authsites.
    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        self.access = None
        if 'access' in kwargs:
            self.access = kwargs.pop('access')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        if hasattr(Contact, 'groups'):
            if self.request.user.is_authenticated():
                self.fields['groups'] = forms.ModelMultipleChoiceField(
                    queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk', flat=True)),
                    required=False)
            else:
                self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)
            if self.access:
                self.fields['groups'] = forms.ModelChoiceField(queryset=self.access.groups.all())

    def perform(self, request, results):
        groups = self.cleaned_data['groups']

        for response in results:
            for g in groups:
                contact = response.message.connection.contact
                if contact:
                    contact.groups.add(g)
        return ('%d Contacts assigned to %d groups.' % (len(results), len(groups)), 'success',)


class BlacklistForm2(ActionForm):
    """ abstract class for all the filter forms"""
    action_label = 'Blacklist/Opt-out Users'

    def perform(self, request, results):
        if request.user and request.user.has_perm('unregister.add_blacklist'):

            connections = Connection.objects.filter(pk__in=results.values_list('connection')).distinct()
            for c in connections:
                Blacklist.objects.get_or_create(connection=c)
                Message.objects.create(status="Q", direction="O", connection=c,
                                       text="Your UReport opt out is confirmed.If you made a mistake,or you want your voice to be heard again,text in JOIN and send it to 8500!All SMS messages are free")
            return ('You blacklisted %d numbers' % len(connections), 'success',)
        else:
            return ("You don't have permissions to blacklist numbers", 'error',)


class SelectPoll(forms.Form):
    """ filter responses to poll  """

    poll = \
        forms.ModelChoiceField(queryset=Poll.objects.exclude(start_date=None).order_by('-pk'))


class SelectCategory(forms.Form):
    category = \
        forms.ModelMultipleChoiceField(queryset=QuerySet())

    def __init__(self, *args, **kwargs):
        categories = kwargs['categories']
        del kwargs['categories']
        super(SelectCategory, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = categories


class SendMessageForm(forms.Form):
    recipients = forms.CharField(label="recepient(s)", required=True, help_text="enter numbers commas separated",
                                 widget=forms.HiddenInput)
    text = forms.CharField(required=True, widget=SMSInput())


class ForwardMessageForm(forms.Form):
    recipients = forms.CharField(label="recepient(s)", required=True, help_text="enter numbers commas separated")
    text = forms.CharField(required=True, widget=SMSInput())


class rangeForm(forms.Form):
    startdate = forms.DateField(('%d/%m/%Y',), label='Start Date', required=False,
                                widget=forms.DateTimeInput(format='%d/%m/%Y', attrs={
                                    'class': 'input',
                                    'readonly': 'readonly',
                                    'size': '15'
                                }))
    enddate = forms.DateField(('%d/%m/%Y',), label='End Date', required=False,
                              widget=forms.DateTimeInput(format='%d/%m/%Y', attrs={
                                  'class': 'input',
                                  'readonly': 'readonly',
                                  'size': '15'
                              }))


class GroupRules(forms.ModelForm):
    class Meta:
        model = AutoregGroupRules
        exclude = ('rule_regex',)


class DownloadForm(forms.Form):
    startdate = forms.DateField(('%d/%m/%Y',), label='Start Date', required=False,
                                widget=forms.DateTimeInput(format='%d/%m/%Y', attrs={
                                    'class': 'input',
                                    'readonly': 'readonly',
                                    'size': '15'
                                }))
    enddate = forms.DateField(('%d/%m/%Y',), label='End Date', required=False,
                              widget=forms.DateTimeInput(format='%d/%m/%Y', attrs={
                                  'class': 'input',
                                  'readonly': 'readonly',
                                  'size': '15'
                              }))

    def export(self, request, queryset, date_field):
        if request.user.has_perm("ureport.can_export"):
            start = self.cleaned_data['startdate']
            end = self.cleaned_data['enddate']
            date = "%s__range" % date_field
            kwargs = dict(date=(start, end))
            data = queryset.filter(**kwargs).values()
            response = ExcelResponse(data=list(data))
            return response


class UreporterSearchForm(FilterForm):
    """ concrete implementation of filter form
        TO DO: add ability to search for multiple search terms separated by 'or'
    """

    searchx = forms.CharField(max_length=100, required=False, label="Free-form search",
                              help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        searchx = self.cleaned_data['searchx'].strip()
        query = UreportContact.objects.none()
        if searchx == "":
            return queryset
        else:
            terms = normalize_query(searchx)
            for term in terms:
                try:
                    term = int(term)
                except Exception:
                    q = queryset.filter(Q(name__icontains=term))
                    query = query | q
                else:
                    q = queryset.filter(Q(mobile=term))
                    query = query | q
        return query


class FilterByGroupForm(FilterForm):
    choices = (('', '-----'),(-1, 'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
    group = forms.ChoiceField(label='', choices = choices, required=False)

    def filter(self, request, queryset):
        group = self.cleaned_data['group']
        if group == '':
            return queryset
        if int(group) == -1 :
            return queryset.filter(group__isnull=True)
        elif int(group) > -1:
            filtered_group = Group.objects.filter(pk=group)
            return queryset.filter(group=filtered_group[0].name)

class FilterByLocationForm(FilterForm):
    choices = (('', '-----'),(-1, 'No Province'),) + tuple([(int(location.pk), location.name) for location in Location.objects.filter(type__slug='district').order_by('name')])


    the_selected_location = forms.ChoiceField(label='', choices = choices, required=False)

    def filter(self, request, queryset):
        province = self.cleaned_data['the_selected_location']
        if province == '':
            return queryset
        if int(province) == -1:
            return queryset.filter(province__isnull=True)
        elif int(province) > -1:
            filtered_location = Location.objects.filter(pk=province)
            return queryset.filter(province=filtered_location[0].name)


class AgeFilterForm(FilterForm):
    """ filter contacts by their age """
    flag = forms.ChoiceField(label='', choices=(('', '-----'), ('==', 'Equal to'), ('>', 'Greater than'), ('<', 'Less than'), ('b', 'Between'),('None', 'N/A')), required=False)
    age = forms.CharField(max_length=20, label="Age", widget=forms.TextInput(attrs={'size': '20'}), required=False)

    def filter(self, request, queryset):
        flag = self.cleaned_data['flag']
        try:
            age = self.cleaned_data['age']
        except:
            age = None
        if flag == '':
            return queryset
        elif flag == '==':
            # we're query this ''' select * from ureport_contact where extract(year from age) = %s '''
            return queryset.extra(where=['extract(year from age)=%s'],
            params=[age])
        elif flag == '>':
            return queryset.extra(where=['extract(year from age)>%s'],
                params=[age])
        elif flag == "<":
            return queryset.extra(where=['extract(year from age)<%s'],
                params=[age])
        elif flag == 'b':
            inputed_age = normalize_query(age)
            minimum = inputed_age[0]
            maximum = inputed_age[-1]
            return queryset.extra(where=['extract(year from age)>%s',
                'extract(year from age)<%s'], params=[minimum, maximum])
        else:
            return queryset.filter(age=None)


class DistrictForm(forms.Form):
    districts = forms.ModelMultipleChoiceField(queryset=Location.objects.filter(type__slug='district').order_by('name'),
                                               required=True)


def get_poll_data(poll):
    yesno_category_names = ['yes', 'no']
    if poll.categories.count():
        category_names = yesno_category_names if poll.is_yesno_poll() else list(
            poll.categories.all().values_list('name', flat=True))
        root = Location.tree.root_nodes()[0]
        data = poll.responses_by_category(root)
        clean_data = {}
        for d in data:
            l = Location.objects.get(pk=d['location_id'])
            clean_data.setdefault(l.pk, {})
            clean_data[l.pk][d['category__name']] = d['value']

        for district_code, values in clean_data.items():
            total = 0
            for c in category_names:
                values.setdefault(c, 0)
            for cat_name, val in values.items():
                total += val
            for cat_name in category_names:
                values[cat_name] = '%d%% ' % int(float(values[cat_name]) * 100 / total)

        return clean_data
    return None


def get_summary(pk, poll_data):
    c = poll_data.get(pk, None)
    return " ".join(["%s said %s" % ( str(c[a]), str(a)) for a in c.keys() if not a in ["uncategorized", "unknown"]])


class TemplateMessage(ActionForm):
    template = forms.CharField(max_length=160, required=True, widget=SMSInput(),
                               help_text="message shd be of form Dear Hon. [insert name]. [insert results ] of people from [insert district] say that lorem ipsum")
    poll = forms.ModelChoiceField(
        queryset=Poll.objects.exclude(start_date=None).exclude(categories=None).order_by('-pk'))

    label = "Send Message"


    def perform(self, request, results):

        if request.user:
            poll = self.cleaned_data['poll']
            contacts = Contact.objects.filter(pk__in=results).exclude(connection=None)
            regex = re.compile(r"(\[[^\[\]]+\])")
            template = self.cleaned_data['template']
            parts = regex.split(template)
            yesno_category_names = ['yes', 'no']
            poll_data = get_poll_data(poll)
            if poll_data:
                import datetime

                key = "templatemsg%s" % str(datetime.datetime.now().isoformat())
                temp_msg, _ = MessageAttribute.objects.get_or_create(name=key)

                for contact in contacts:

                    if contact.reporting_location and poll_data.get(contact.reporting_location.pk, None):
                        d = {
                            'name': contact.name.split()[-1],
                            'district': contact.reporting_location.name,
                            'results': get_summary(contact.reporting_location.pk, poll_data)

                        }

                        message = ""
                        for p in parts:
                            if p.strip().startswith("["):

                                message = message + d[p.replace("[", "").replace("]", "").strip().rsplit()[1]]
                            else:
                                message = message + p

                        message = Message.objects.create(status="P", direction="O",
                                                         connection=contact.default_connection, text=message)
                        msg_a = MessageDetail.objects.create(message=message, attribute=temp_msg, value='comfirm')

                return (mark_safe(
                    'Message is going to be sent to   %d contacts .<a href="/comfirmmessages/%s/">Comfirm Sending </a>' % (
                        len(results), key)), 'success',)
            else:
                return ("some thing went wrong", 'error',)

        else:
            return ("you need to be logged in ", 'error',)


class GroupsFilter(forms.Form):
    def __init__(self, *args, **kwargs):
        if 'request' in kwargs:
            request = kwargs.pop('request')
        super(GroupsFilter, self).__init__(*args, **kwargs)
        try:
            access = Access.objects.get(user=request.user)
            self.fields['group_list'] = forms.ModelMultipleChoiceField(queryset=access.groups.order_by('name'),
                                                                       required=False)
        except Access.DoesNotExist, e:
            print "Access DoesNotExist", e
            self.fields['group_list'] = forms.ModelMultipleChoiceField(queryset=Group.objects.order_by('name'),
                                                                       required=False)
        except UnboundLocalError, e:
            print "UnboundLocalError:", e
            self.fields['group_list'] = forms.ModelMultipleChoiceField(queryset=Group.objects.order_by('name'),
                                                                       required=False)
        except Exception, e:
            print "General Exception: ", e
            self.fields['group_list'] = forms.ModelMultipleChoiceField(queryset=Group.objects.order_by('name'),
                                                                       required=False)


class PushToMtracForm(ActionForm):
    action_label = "Push Selected Messages to Mtrac"

    def perform(self, request, results):
        results = set([r.pk for r in results])
        tasks.push_to_mtrac.delay(results)
        return "%d Messages were pushed to mtrac" % len(results), "success"


class ExportToExcelForm(ActionForm):
    action_label = "Generate the excel file"

    def perform(self, request, results):
        data = results.values()
        return ExcelResults(
                    data=data,
                    output_name='exported_results.xlsx',
                    write_to_file=False,
                )
