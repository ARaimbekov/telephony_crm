import csv
import re
import string
import random
from leads.models import Number, Atc, Lead, Company, Apparats


def migrate_numbers(file):
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                line = line.split(';')
                number = line[1].strip()
                atc_ip = line[6].strip()

                if line[1] and line[6]:
                    atc = Atc.objects.filter(ip_address=atc_ip).first()
                    Number.objects.create(name=number, atc=atc).save()
            except Exception as err:
                print(err, line)


def migrate_mac(file):
    company = Company.objects.filter(name='OOO "ИНК"').first()
    user = 'system'
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                line = line.strip().split(';')
                number = Number.objects.filter(name=line[1].strip()).first()
                mac_address = line[2].strip().lower()
                phone_line = line[4].strip()
                password = line[5].strip()
                atc_ip = line[6].strip()
                full_name = line[7].strip()
                atc = Atc.objects.filter(ip_address=atc_ip).first()

                param = {
                    'phone_number': number,
                    'mac_address': mac_address,
                    'line': phone_line,
                    'reservation': False,
                    'passwd': password,
                    'updated_user': user,
                    'created_user': user,
                }

                if re.match(r'^\w*\s\w[.]\w[.]', full_name):
                    full_name = full_name.split()
                    param['last_name'] = full_name[0][:20]
                    _io = full_name[1].split('.')
                    param['first_name'] = _io[0]
                    param['patronymic_name'] = _io[1]
                else:
                    param['last_name'] = full_name[:20]

                if len(mac_address) != 12 or mac_address == '000000000000':
                    param['reservation'] = True

                mac = Lead.objects.create(**param)
                mac.company.add(company)
                mac.atc.add(atc)

                if param['reservation']:
                    letters = string.digits
                    while True:
                        try:
                            param['mac_address'] = '000000' + ''.join(random.choice(letters) for _ in range(6))
                            mac.mac_address = param['mac_address']
                            mac.phone_model.add(Apparats.objects.filter(name='Телефон_отсутствует').first())
                            mac.save()
                            break
                        except Exception:
                            pass
                else:
                    mac.phone_model.add(Apparats.objects.filter(name=line[3]).first())
                    mac.save()
            except Exception as err:
                print(err, line)


def change_atc(file, atc_id):
    import psycopg2
    conn = psycopg2.connect(
        database="postgres",
        user='postgres',
        password='postgres',
        host='10.90.42.234',
        port='15432',
    )

    cursor = conn.cursor()
    numbers = open(file, 'r')
    for number in numbers:
        number = number[:5]
        insert_sql_1 = '''
            UPDATE leads_number
            SET atc_id=%s
            FROM leads_number as LN
            WHERE leads_number.name in (%s);'''
        cursor.execute(insert_sql_1, [atc_id, number.strip()])
        conn.commit()

        insert_sql_2 = ''' UPDATE leads_lead_atc SET atc_id = %s 
            FROM leads_lead_atc as LA 
            WHERE leads_lead_atc.lead_id in (SELECT LA.lead_id FROM leads_lead_atc AS LA JOIN leads_lead on LA.lead_id = leads_lead.id
            JOIN leads_number on leads_lead.phone_number_id = leads_number.id
            WHERE leads_number.name in (%s));'''
        cursor.execute(insert_sql_2, [atc_id, number.strip()])
        conn.commit()
