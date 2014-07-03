#!/usr/bin/python
# -*- coding: utf-8 -*-

from xlrd import open_workbook
from uganda_common.utils import assign_backend
#, assign_backend_test
from script.utils.handling import find_closest_match
from rapidsms.models import Connection, Backend, Contact
from rapidsms.contrib.locations.models import Location
from django.contrib.auth.models import Group
import datetime
#import logging




def parse_header_row(worksheet, fields):
    #This method build a dictionary in which keys are the valid names of columns of the uploaded excel file (excel file of user profiles)
    #and values are columns.
    #Fields is a list of words which can be names of columns of the excel file which contains user profiles 
    field_cols = {}
    for col in range(worksheet.ncols):
        value = str(worksheet.cell(0, col).value).strip()
        if value.lower() in fields:
            field_cols[value.lower()] = col
    return field_cols


def parse_telephone(row, worksheet, cols):
    try:
        number = str(worksheet.cell(row, cols['telephone number'
        ]).value)
    except KeyError:
        number = str(worksheet.cell(row, cols['telephone']).value)
    return number.replace('-', '').strip().replace(' ', '')

def parse_telephone_number(row, worksheet, cols):
    try:
        number = str(worksheet.cell(row, cols['telephone number'
        ]).value)
    except KeyError:
        number = str(worksheet.cell(row, cols['number']).value)
    return number.replace('-', '').strip().replace(' ', '')


def parse_name(row, worksheet, cols):
    v=worksheet.cell(row, cols['name']).value
    print("v")
    print(v)
    try:
        name = str(worksheet.cell(row, cols['company name'
        ]).value).strip()
    except KeyError:
        name = str(worksheet.cell(row, cols['name']).value).strip()
    if name.__len__() > 0:

    #        name = str(worksheet.cell(row, cols['name']).value)

        return ' '.join([t.capitalize() for t in name.lower().split()])
    else:
        return 'Anonymous User'


#def parse_district(row, worksheet, cols):
#    return str(worksheet.cell(row, cols['district']).value)
def parse_district(row, worksheet, cols):
    return str(worksheet.cell(row, cols['province']).value)

def parse_commune(row, worksheet, cols):
    return str(worksheet.cell(row, cols['commune']).value)
def parse_colline(row, worksheet, cols):
    return str(worksheet.cell(row, cols['colline']).value)
def parse_language(row, worksheet, cols):
    return str(worksheet.cell(row, cols['language']).value)

def parse_village(row, worksheet, cols):
    return str(worksheet.cell(row, cols['village']).value)

def parse_group(row, worksheet, cols):
    return str(worksheet.cell(row, cols['group']).value)

def parse_birthdate(row, worksheet, cols):
    try:
        age = int(worksheet.cell(row, cols['age']).value)
        birthdate = '%d/%d/%d' % (datetime.datetime.now().day,
                                  datetime.datetime.now().month,
                                  datetime.datetime.now().year - age)
        return datetime.datetime.strptime(birthdate.strip(), '%d/%m/%Y')
    except ValueError:
        return None


def parse_gender(row, worksheet, cols):
    gender = str(worksheet.cell(row, cols['gender']).value)
    return (gender.upper()[:1] if gender else None)

def handle_excel_file(file, group, fields):
    if file:
        excel = file.read()
        workbook = open_workbook(file_contents=excel)
        worksheet = workbook.sheet_by_index(0)
        cols = parse_header_row(worksheet, fields)
        contacts = []
        duplicates = []
        invalid = []
        info = ''

        if not group:
            default_group =\
            Group.objects.filter(name__icontains='ureporters')[0]
            group = default_group

        if worksheet.nrows > 1:
            validated_numbers = []
            for row in range(1, worksheet.nrows):
                numbers = parse_telephone(row, worksheet, cols)
                for raw_num in numbers.split('/'):
                    if raw_num[-2:] == '.0':
                        raw_num = raw_num[:-2]
                    if raw_num[:1] == '+':
                        raw_num = raw_num[1:]
                    if len(raw_num) >= 9:
                        validated_numbers.append(raw_num)
            duplicates =\
            Connection.objects.filter(identity__in=validated_numbers).values_list('identity'
                , flat=True)

            for row in range(1, worksheet.nrows):
                numbers = parse_telephone(row, worksheet, cols)
                if len(numbers) > 0:
                    contact = {}
                    contact['name'] = parse_name(row, worksheet, cols)
                    district = (parse_district(row, worksheet,
                        cols) if 'district' in fields else None)
                    village = (parse_village(row, worksheet,
                        cols) if 'village' in fields else None)
                    birthdate = (parse_birthdate(row, worksheet,
                        cols) if 'age' in fields else None)
                    gender = (parse_gender(row, worksheet,
                        cols) if 'gender' in fields else None)
                    if district:
                        contact['reporting_location'] =\
                        find_closest_match(district,
                            Location.objects.filter(type__slug='district'
                            ))
                    if village:
                        contact['village'] =\
                        find_closest_match(village,
                            Location.objects)
                    if birthdate:
                        contact['birthdate'] = birthdate
                    if gender:
                        contact['gender'] = gender
                    if group:
                        contact['groups'] = group

                    for raw_num in numbers.split('/'):
                        if raw_num[-2:] == '.0':
                            raw_num = raw_num[:-2]
                        if raw_num[:1] == '+':
                            raw_num = raw_num[1:]
                        if len(raw_num) >= 9:
                            if raw_num not in duplicates:
                                (number, backend) =\
                                assign_backend(raw_num)
                                if number not in contacts and backend\
                                is not None:
                                    Connection.bulk.bulk_insert(send_pre_save=False,
                                        identity=number, backend=backend, contact=contact)
                                    contacts.append(number)
                                elif backend is None:
                                    invalid.append(raw_num)
                        else:
                            invalid.append(raw_num)

            connections =\
            Connection.bulk.bulk_insert_commit(send_post_save=False,
                autoclobber=True)
            contact_pks = connections.values_list('contact__pk',
                flat=True)

            if len(contacts) > 0:
                info = 'Contacts with numbers... '\
                       + ' ,'.join(contacts)\
                + ''' have been uploaded !

'''
            if len(duplicates) > 0:
                info = info\
                       + 'The following numbers already exist in the system and thus have not been uploaded: '\
                       + ' ,'.join(duplicates) + '''

'''
            if len(invalid) > 0:
                info = info\
                       + 'The following numbers may be invalid and thus have not been added to the system: '\
                       + ' ,'.join(invalid) + '''

'''
        else:
            info =\
            'You seem to have uploaded an empty excel file, please fill the excel Contacts Template with contacts and upload again...'
    else:
        info = 'Invalid file'
    return info







def handle_excel_file_update(file, fields):
    if file:
        excel = file.read()
        workbook = open_workbook(file_contents=excel)
        worksheet = workbook.sheet_by_index(0)
        columns_name = parse_header_row(worksheet, fields)
        contacts = []
        duplicates = []
        invalid = []
        info = ''
        numbers_uploaded = 0
        numbers_invalid = 0

        if worksheet.nrows > 1:
            validated_numbers = [] #This is a list of numbers which are valid
            invalid = [] #This is a list of numbers which are invalid
            for row in range(1, worksheet.nrows):
                #Check first if the number is valid
                numbers = parse_telephone_number(row, worksheet, columns_name)
                if len(numbers) > 0:
                    for raw_num in numbers.split('/'):
                        if raw_num[-2:] == '.0':
                            raw_num = raw_num[:-2]
                        if raw_num[:1] == '+':
                            raw_num = raw_num[1:]
                        if len(raw_num) < 9:
                            invalid.append(raw_num)
                        if raw_num not in invalid:
                    	    try:
                                connection = Connection.objects.filter(identity=unicode(raw_num))[0]
                                the_contact = connection.contact
                                if the_contact is None:
                        	       invalid.append(raw_num)
                                       print(1)
                                       print(raw_num)
                    	    except IndexError:
                        	   invalid.append(raw_num)
                                   print(2)
                                   print(raw_num)
                                   

                            
                            #If the phone number is valid, we update properties of the user to whom belongs this phone number
                            #after putting it on the list of valid phone numbers
                            if raw_num not in invalid:
                                validated_numbers.append(raw_num)
 

                                if "name" in columns_name:
                                	name = parse_name(row, worksheet, columns_name)
                                	if len(name)>95:
                                    		name = name[0:95]
					the_contact.name=name
					

    				if "province" in columns_name:
					province = parse_district(row, worksheet, columns_name)
                                	province = province.capitalize()
                                	location = Location.objects.filter(name=province)
                                	if location :
                                    		location=location[0]
                                	else :
                                    		location = Location.objects.create(name=province)
                                        the_contact.reporting_location = location 
										
			
				if "commune" in columns_name:
                                	commune = parse_commune(row, worksheet, columns_name)
                                	commune = commune.capitalize()
                                	location = Location.objects.filter(name=commune)
                                	if location :
                                    		location=location[0]
                                	else :
                                    		location = Location.objects.create(name=commune)
					the_contact.commune=location
					

				if "colline" in columns_name:
                                	colline = parse_colline(row, worksheet, columns_name)
	                                colline = colline.capitalize()
                                	location = Location.objects.filter(name=colline)
                                	if location :
                                    		location=location[0]
                                	else :
                                    		location = Location.objects.create(name=colline)
					the_contact.colline=location



				if "language" in columns_name:
                                	language = parse_language(row, worksheet, columns_name)
					the_contact.language=language

				if "age" in columns_name:
                                	birthdate = parse_birthdate(row, worksheet, columns_name)
					the_contact.birthdate=birthdate

				if "gender" in columns_name:
                                	gender = parse_gender(row, worksheet, columns_name)
     					the_contact.gender=gender

				if "group" in columns_name:
                                	group = parse_group(row, worksheet, columns_name)
                                	right_group=Group.objects.filter(name='Other Reporters')[0] #This is the default group
                                	if group:
                                   		g1 = Group.objects.filter(name=group)[0]
                                    		if g1 :
                                        		right_group=g1
					the_contact.groups.add(right_group)
                                
                           
                                the_contact.save()


                                contacts.append(raw_num)


            numbers_uploaded = len(contacts)
            if len(contacts) > 0:
                info = str(len(contacts)) + ''' have been uploaded ! '''
            numbers_invalid = len(invalid)
            if len(invalid) > 0:
                info = info + str(len(invalid)) + ' numbers may be invalid and thus have not been considered'
        else:
            info =\
            'You seem to have uploaded an empty excel file, please fill the excel Contacts Template with contacts and upload again...'
        return '%s . So we have %s valid contacts and %s invalid contacts updated' % (info, str(numbers_uploaded) , str(numbers_invalid))
    else:
        info = 'Invalid file'

    return info
