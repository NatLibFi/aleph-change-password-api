#!/usr/bin/env python2.7
# -*- coding: utf8 -*-

import unittest
import imp
import sys
from contextlib import contextmanager, nested
from StringIO import StringIO
from mock import patch, Mock, call
import os
import urllib2
import cx_Oracle
import json
import subprocess

changeAlephUserPassword = imp.load_source('changeAlephUserPassword', 'change-aleph-user-password.cgi')

changeAlephUserPassword.ALEPH_URL = 'http://test.com'
changeAlephUserPassword.ALEPH_USER_LIBRARY = 'usr'
changeAlephUserPassword.ALEPH_USER_DB = 'usr'
changeAlephUserPassword.DB_CONFIG = 'aleph/aleph@127.0.0.1:1521/ALEPH20'
changeAlephUserPassword.FILES_DIR = '/tmp/'
changeAlephUserPassword.FILE_PREFIX = 'user/'
changeAlephUserPassword.LOG_DIR = 'logs/'
changeAlephUserPassword.PASSWORD_VALIDATION = '^[\w$?*!,\-\.\u00C4\u00E4\u00D6\u00F6\u00C5\u00E5]*$'
changeAlephUserPassword.MAX_LENGTH = 10
changeAlephUserPassword.MIN_LENGTH = 8

class TestClass(unittest.TestCase):
  def test_validate_password_valid(self):
    result, error_message = changeAlephUserPassword.validate_password('1234567890')

    self.assertTrue(result)
    self.assertIsNone(error_message)

  def test_validate_password_too_short(self):
    result, error_message = changeAlephUserPassword.validate_password('aaaaaaa')

    self.assertFalse(result)

    self.assertEqual(error_message, 'Password must be atleast 8 characters long')

  def test_validate_password_too_long(self):
    result, error_message = changeAlephUserPassword.validate_password('12345678901')

    self.assertFalse(result)
    self.assertEqual(error_message, 'Password can not be longer than 10 characters')

  def test_validate_password_illegal_characters(self):
    result, error_message = changeAlephUserPassword.validate_password('12345#789')

    self.assertFalse(result)
    self.assertEqual(error_message, 'Password contains illegal characters')

  @patch('urllib2.urlopen', return_value=open('test/auth.xml', 'r'))
  def test_validate_user_valid(self, mock_urlib2_urlopen):
    result = changeAlephUserPassword.validate_user('test', 'password')

    mock_urlib2_urlopen.assert_called_once_with('%s/X?op=user-auth&library=%s&staff_user=test&staff_pass=password' % (changeAlephUserPassword.ALEPH_URL, changeAlephUserPassword.ALEPH_USER_LIBRARY))

    self.assertTrue(result)

  @patch('urllib2.urlopen', return_value=open('test/auth_error.xml', 'r'))
  def test_validate_user_invalid(self, mock_urlib2_urlopen):
    result = changeAlephUserPassword.validate_user('test', 'password')

    mock_urlib2_urlopen.assert_called_once_with('%s/X?op=user-auth&library=%s&staff_user=test&staff_pass=password' % (changeAlephUserPassword.ALEPH_URL, changeAlephUserPassword.ALEPH_USER_LIBRARY))

    self.assertFalse(result)

  @patch('cx_Oracle.connect')
  def test_fetch_user_from_db(self, mock_cx_oracle_connect):
    row = ('TEST', 'GROUP', 'password')
    desc = [
      ('Z66_REC_KEY', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0),
      ('Z66_USER_LIBRARY', cx_Oracle.FIXED_CHAR, 5, 5, None, None, 0),
      ('Z66_USER_PASSWORD', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
    ]

    mock_cx_oracle_connect.return_value.cursor.return_value.fetchone.return_value = row
    mock_cx_oracle_connect.return_value.cursor.return_value.description = desc

    result = changeAlephUserPassword.fetch_user_from_db('test')

    mock_cx_oracle_connect.return_value.cursor.return_value.execute.assert_called_once_with("SELECT * FROM usr.z66 WHERE Z66_REC_KEY = 'TEST'")
    self.assertEqual(result, [
      {
        'value': row[0],
        'desc': desc[0]
      },
      {
        'value': row[1],
        'desc': desc[1]
      },
      {
        'value': row[2],
        'desc': desc[2]
      }
    ])

  def test_format_row(self):
    row = [
      {
        'value': 'TEST',
        'desc': ('Z66_REC_KEY', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      },
      {
        'value': 'GROUP',
        'desc': ('Z66_USER_LIBRARY', cx_Oracle.FIXED_CHAR, 5, 5, None, None, 0)
      },
      {
        'value': 'test',
        'desc': ('Z66_USER_PASSWORD', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      }
    ]

    result = changeAlephUserPassword.format_row(row)

    self.assertEqual(result, 'TEST      GROUPtest      ')

  @patch('changeAlephUserPassword.open')
  @patch('changeAlephUserPassword.uuid4', return_value='1cf1bc5f-2fe2-4e05-8f0d-6150abe7d61b')
  def test_write_input_file(self, mock_uuid4, mock_open):
    result = changeAlephUserPassword.write_input_file('test')

    mock_open.assert_called_once_with('%s%s%s' % (changeAlephUserPassword.FILES_DIR, changeAlephUserPassword.FILE_PREFIX, '1cf1bc5'), 'w')
    mock_open.return_value.write.assert_called_once_with('test')
    mock_open.return_value.close.assert_called()
    self.assertEqual(result, '1cf1bc5')

  @patch('subprocess.Popen')
  def test_execute_program(self, mock_subprocess_popen):
    mock_subprocess_popen.return_value.communicate.return_value = ('test_output', 'test_error')

    result = changeAlephUserPassword.execute_program('test')

    mock_subprocess_popen.assert_called_once_with(['/usr/bin/env', 'csh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    mock_subprocess_popen.return_value.stdin.write.assert_has_calls([call('source /exlibris/aleph/a20_2/alephm/.cshrc\n'), call('/exlibris/aleph/a20_2/aleph/proc/p_file_06 USR00,user/test,z66,UPDATE,NO-FIX,Y,Y,\n'), call('exit\n')])

    self.assertEqual(result, ('test_output', 'test_error'))

  @patch('datetime.datetime')
  @patch('changeAlephUserPassword.open')
  def test_write_input_file(self, mock_open, mock_datetime):
    mock_datetime.now.return_value = '2017-11-24 06:53:21.067790'

    result = changeAlephUserPassword.write_log_file('test', 'test_formatted_row', 'test_output', 'test_error')

    mock_open.assert_called_once_with('%stest-2017-11-24 06:53:21.067790.log' % changeAlephUserPassword.LOG_DIR, 'w')
    mock_open.return_value.write.assert_called_once_with(json.dumps({
      'username': 'test',
      'formatted_row': 'test_formatted_row',
      'output': 'test_output',
      'error': 'test_error',
    }))

    mock_open.return_value.close.assert_called_once()

  @patch('sys.stdout', new_callable=StringIO)
  @patch.dict(os.environ, {'REQUEST_METHOD': 'GET'})
  def test_not_found(self, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 404\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '404 Not Found\n')

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()
  
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('sys.stdin', new=StringIO('{}'))
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_bad_request(self, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 400\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '400 Bad Request\n')

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()
    
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('sys.stdin', new=StringIO('{"username":"test","password":"test","new_password":"12345678#"}'))
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_invalid_password(self, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 400\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '400 Bad Request: Password contains illegal characters\n')

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()
    
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('sys.stdin', new=StringIO('{"username":"test","password":"test","new_password":"testtest"}'))
  @patch('changeAlephUserPassword.validate_user', return_value=False)
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_unauthorized(self, mock_validate_user, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 401\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '401 Unauthorized\n')

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()

    mock_validate_user.assert_called_once_with('test', 'test')
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('sys.stdin', new=StringIO('{"username":"test","password":"test","new_password":"testtest"}'))
  @patch('changeAlephUserPassword.validate_user', side_effect=urllib2.URLError('test'))
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_validation_error(self, mock_validate_user, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 500\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '500 Internal Server Error\n')

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()

    mock_validate_user.assert_called_once_with('test', 'test')
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('sys.stdin', new=StringIO('{"username":"test","password":"test","new_password":"testtest"}'))
  @patch('os.remove')
  @patch('changeAlephUserPassword.write_log_file')
  @patch('changeAlephUserPassword.execute_program', return_value=(open('test/output_error.txt', 'r').read(), None))
  @patch('changeAlephUserPassword.write_input_file', return_value='008a2cc')
  @patch('changeAlephUserPassword.fetch_user_from_db')
  @patch('changeAlephUserPassword.validate_user', return_value=True)
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_program_error(self, mock_validate_user, mock_fetch_user_from_db, mock_write_input_file, mock_execute_program, mock_write_log_file, mock_os_remove, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 500\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       '500 Internal Server Error\n')

    mock_fetch_user_from_db.return_value = [
      {
        'value': 'TEST',
        'desc': ('Z66_REC_KEY', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      },
      {
        'value': 'GROUP',
        'desc': ('Z66_USER_LIBRARY', cx_Oracle.FIXED_CHAR, 5, 5, None, None, 0)
      },
      {
        'value': '',
        'desc': ('Z66_USER_PASSWORD', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      }
    ]

    expected_formatted_row_clean = 'TEST      GROUP          '
    expected_formatted_row = 'TEST      GROUPtesttest  '

    with self.assertRaises(SystemExit): 
      changeAlephUserPassword.main()

    mock_validate_user.assert_called_once_with('test', 'test')
    mock_fetch_user_from_db.assert_called_once_with('test')
    mock_write_input_file.assert_called_once_with(expected_formatted_row)
    mock_execute_program.assert_called_once_with(mock_write_input_file.return_value)
    mock_write_log_file.assert_called_once_with('test', expected_formatted_row_clean, mock_execute_program.return_value[0], mock_execute_program.return_value[1])
    mock_os_remove.assert_called_once_with('/tmp/user/008a2cc')
    self.assertEqual(mock_stdout.getvalue(), expected_output)

  @patch('sys.stdout', new_callable=StringIO)
  @patch('os.remove')
  @patch('changeAlephUserPassword.write_log_file')
  @patch('changeAlephUserPassword.execute_program', return_value=(open('test/output.txt', 'r').read(), None))
  @patch('changeAlephUserPassword.write_input_file', return_value='008a2cc')
  @patch('changeAlephUserPassword.fetch_user_from_db')
  @patch('changeAlephUserPassword.validate_user', return_value=True)
  @patch('sys.stdin', new=StringIO('{"username":"test","password":"test","new_password":"testtest"}'))
  @patch.dict(os.environ, {'REQUEST_METHOD': 'POST'})
  def test_program_success(self, mock_validate_user, mock_fetch_user_from_db, mock_write_input_file, mock_execute_program, mock_write_log_file, mock_os_remove, mock_stdout):
    expected_output = ('Content-Type: text/plain\n'
                       'Status: 200\n'
                       'Cache-Control: no-cache, no-store, max-age=0\n\n'
                       'ok\n')

    mock_fetch_user_from_db.return_value = [
      {
        'value': 'TEST',
        'desc': ('Z66_REC_KEY', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      },
      {
        'value': 'GROUP',
        'desc': ('Z66_USER_LIBRARY', cx_Oracle.FIXED_CHAR, 5, 5, None, None, 0)
      },
      {
        'value': '',
        'desc': ('Z66_USER_PASSWORD', cx_Oracle.FIXED_CHAR, 10, 10, None, None, 0)
      }
    ]

    expected_formatted_row_clean = 'TEST      GROUP          '
    expected_formatted_row = 'TEST      GROUPtesttest  '
    
    changeAlephUserPassword.main()

    mock_validate_user.assert_called_once_with('test', 'test')
    mock_fetch_user_from_db.assert_called_once_with('test')
    mock_write_input_file.assert_called_once_with(expected_formatted_row)
    mock_execute_program.assert_called_once_with(mock_write_input_file.return_value)
    mock_write_log_file.assert_called_once_with('test', expected_formatted_row_clean, mock_execute_program.return_value[0], mock_execute_program.return_value[1])
    mock_os_remove.assert_called_once_with('/tmp/user/008a2cc')
    self.assertEqual(mock_stdout.getvalue(), expected_output)

if __name__ == '__main__':
  unittest.main()