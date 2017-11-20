#!/usr/bin/env python
# -*- coding: utf8 -*-

import cgi
import sys
import json
import cgitb
import os
import urllib2
import xml.etree.ElementTree as ElementTree
import cx_Oracle
from uuid import uuid4
import subprocess
import datetime
import re

ALEPH_URL = 'http://libtest.csc.fi:8992'
ALEPH_USER_LIBRARY = 'usr00'
DB_CONFIG = 'aleph/aleph@10.0.2.2:1521/ALEPH20'
FILES_DIR = '/vagrant/tmp/'
FILE_PREFIX = 'user/'
LOG_DIR = '/vagrant/logs/'

db = cx_Oracle.connect(DB_CONFIG)

cgitb.enable()

def start_http(mimetype=None, headers={}):
  if mimetype:
    print 'Content-Type: %s' % mimetype 
  for name, value in headers.items():
    print '%s: %s' % (name, value)
  print 'Cache-Control: no-cache, no-store, max-age=0'
  print  # end of headers

def return_error(code, message):
    start_http('text/plain', {'Status': code})
    print code, message
    sys.exit()

def validate_user(username, password):
  url = '%s/X?op=user-auth&library=%s&staff_user=%s&staff_pass=%s' % (ALEPH_URL, ALEPH_USER_LIBRARY, username, password)

  xml = urllib2.urlopen(url).read()

  xml = ElementTree.fromstring(xml)

  errorOccurred = xml.find('./error') != None

  if errorOccurred:
    return False

  credentialsValid = xml.find('./reply').text == 'ok'

  if not credentialsValid:
    return False

  userLibrary = xml.find('./z66/z66-user-library').text
  name = xml.find('./z66/z66-name').text
  department = xml.find('./z66/z66-department').text
  email = xml.find('./z66/z66-email').text

  return {
    'userLibrary': userLibrary,
    'name': name,
    'department': department,
    'email': email
  }

def fetch_user_from_db(username):
  cursor = db.cursor() 

  cursor.execute("SELECT * FROM usr00.z66 WHERE Z66_REC_KEY = '%s'" % username.upper())
 
  result = []

  for col, description in zip(cursor.fetchone(), cursor.description):
    result.append({
      'value': col,
      'desc': description
    })

  return result

def format_row(row):
  result = []
  for col in row:
    val = col['value']
    desc = col['desc']

    if val is None:
      val = ' ' * desc[2]
    elif type(val) != str:
      val = str(val).ljust(desc[2])
    else:
      val = val.ljust(desc[2])

    result.append(val)

  return ''.join(result)

def write_log_file(username, formatted_row, output, error):
  f = open('%s%s-%s.log' % (LOG_DIR, username, datetime.datetime.now()), 'w')

  obj = {
    'username': username,
    'formatted_row': formatted_row,
    'output': output,
    'error': error,
  }

  f.write(json.dumps(obj))

  f.close()

if os.environ['REQUEST_METHOD'] != 'POST':
  return_error(404, 'Not found')

try:
  data = json.loads(sys.stdin.read())

  username = data['username']
  password = data['password']
  new_password = data['new_password']

  if username == '' or password == '' or new_password == '':
    raise
except:
  return_error(400, 'Bad Request')

user = validate_user(username, password)

if not user:
  return_error(401, 'Unauthorized')

db_user = fetch_user_from_db(username)

db_user[2]['value'] = new_password

file_id = str(uuid4())[:7]

f = open('%s%s%s' % (FILES_DIR, FILE_PREFIX, file_id), 'w')

formatted_row = format_row(db_user)

f.write(formatted_row)

f.close()

p = subprocess.Popen(['/usr/bin/env', 'csh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
p.stdin.write('source /exlibris/aleph/a20_2/alephm/.cshrc\n')
p.stdin.write('/exlibris/aleph/a20_2/aleph/proc/p_file_06 USR00,%s%s,z66,UPDATE,NO-FIX,Y,Y,\n' % (FILE_PREFIX, file_id))
p.stdin.write('exit')

(output, error) = p.communicate()

write_log_file(username, formatted_row, output, error)

failure = False

for pattern in ['Param Errors Found:', 'Param Initialization Failure, Exiting !!!']:
  if (re.search(pattern, output, flags=re.MULTILINE)):
    failure = True
    break

if failure:
  return_error(500, 'Internal Server Error')

start_http()