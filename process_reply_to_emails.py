#!/usr/bin/python
""" Test retrieving, parsing, and processing emails sent via the reply-to conversation via
		email functionality
	Assumes reply-to email feature is properly configured and that either; unprocessed emails exist,
		or a relevant email is sent while this script is running
	
	Usage:
		process_reply_to_emails.py  [--check_count <num_of_times_to_check_emails>]
							[--check_freq <num_of_seconds_before_checking_again>]

	Options:
		-h --help			Show this screen.
		--check_count		Num of times to check mail. Defaults to 5 times
		--check_freq		Num of seconds between each mail check. Defaults to 5 seconds

"""

import argparse
import sys
import traceback
import time

import alation_conf
import bootstrap_rosemeta

from bs4 import BeautifulSoup
from django.utils.html import escape

from alation_mailbox.message import find_outlook_quoted_header
from alation_mailbox.message import Message
from alation_mailbox.message import TEXT_REPLY_PATTERNS
from alation_mailbox.models import get_mailbox
from alation_mailbox.utils import _handle_request
from alation_mailbox.utils import InvalidEmailError
from alation_mailbox.utils import MAILBOX_NAME
from alation_mailbox.utils import reply_via_email_enabled


DEFAULT_NUM_MAIL_CHECKS = 5
DEFAULT_MAIL_CHECK_FREQUENCY = 5  # seconds
ENDC = '\033[0m'
GREEN = '\033[0;32m'
HTML_REPLY_PATTERNS = [
	{'name': 'div', 'class_': 'gmail_extra'},  # gmail
	{'name': 'div', 'class_': 'gmail_quote'},  # outlook ios
	# 10/06/17 (qc): move this generic outlook pattern before others because the one after it
	#   sometimes extracts empty content from a user's email
	{'name': find_outlook_quoted_header},  # outlook 2016
	{'name': 'a', 'attrs': {'name': '_MailEndCompose'}},  # outlook
	{'name': 'span', 'id': 'OLK_SRC_BODY_SECTION'},  # outlook MacOS
	{'name': 'hr'},  # outlook.com
]
# max line wrap to consider when looking for reply patterns
MAX_LINE_WRAP = 2
OKBLUE = '\033[94m'
RED ='\033[0;31m'
REPLY_MESSAGE = '- Please type your reply above this line -'

def print_with_color(mssg, color=OKBLUE):
	"""Print colored message on terminal

	Args:
	    mssg (TYPE): message to print
	    color (str, optional): Color ascii. Defaults to that of OKBLUE
	"""

	print "{}    {} {}".format(color, mssg, ENDC)

def _extract_content(email_message):
	# first try to use html tag to remove quoted content
	if email_message.html:
		print_with_color("Detected HTML message... Removing quoted content")
		soup = BeautifulSoup(email_message.html, 'html.parser')
		raw = unicode(soup)
		patterns = (alation_conf.conf['alation.email.original_html_message_patterns'] +
					HTML_REPLY_PATTERNS)
		for tag in patterns:
			reply_header = soup.find(**tag)
			if not reply_header:
				continue
			print_with_color("	        Found reply header in tag: {}".format(tag))
			offset = raw.index(unicode(reply_header))
			if not offset:
				continue
			raw = raw[:offset]
			soup = BeautifulSoup(raw[:offset], 'html.parser')
			return unicode(soup)
	# if html text is not present or no quoted message is detected, fall back to plain text
	if email_message.text:
		print_with_color("HTML text not present or didn't find quoted message...")
		lines = []
		found = None
		for line in email_message.text.splitlines():
			if (REPLY_MESSAGE in line):
				break
			lines.append(line)
			for regex in Message._get_text_reply_regex():
				for count in range(1, MAX_LINE_WRAP + 1):
					full_line = ''.join(lines[-count:])
					if regex.search(full_line):
						new_offset = len(lines) - count
						if not found or found > new_offset:
							found = new_offset
						break
			if found is not None:
				lines = lines[:found]
				break
		return '<br>'.join([escape(line).replace(' ', '&nbsp;') for line in lines])
	print_with_color("    Text not present in message, falling back to full html of message")
	# if text is not present in the message, fallback to full html
	return email_message.html

def _process_message(email_message, parsed_content):
	alation_message = Message(email_message)
	alation_message._content = parsed_content
	sender = email_message.from_address[0]
	# avoid processing automated emails(failed delivery, oof message, etc)
	if alation_message.is_auto_generated:
		return
	user = alation_message.user
	if not user:
		raise InvalidEmailError(
			'We could not find an Alation user with the email address "%s".'
			' Please try sending this from your Alation account email.' % sender)
	if not user.is_active:
		raise InvalidEmailError(
			'Your Alation account has not been activated.'
			' Please contact your system adminstrator.')
	request = alation_message.request
	if not request:
		raise InvalidEmailError(
			'Something went wrong when trying to process your message.'
			' Try again by replying to the original email (not a forwarded message).')
	content = alation_message.content
	if not content:
		raise InvalidEmailError(
			'Something went wrong when trying to read your message.'
			' Only plain-text in emails is currently supported.')
	_handle_request(user, request, content)

def _print_message_details(message):
	print u"	Message From: {}".format(message.from_header)
	print u"	Message To: {}".format(message.to_header)
	print u"	Message Address: {}".format(message.address)
	print u"	Message Subject: {}".format(message.subject)
	print u"	Message Text: {}".format(message.text)
	print u"	Message Html: {}".format(message.html)

def get_traceback():
	exc_type, exc_value, exc_traceback = sys.exc_info()
	traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)

def main(args):
	if not reply_via_email_enabled():
		print("Reply Via Email not configured. Exiting.")
		quit()

	try:
		mailbox = get_mailbox(name=MAILBOX_NAME)
		num_attempts = args.num_times_to_check_mail
		for i in range(1, num_attempts + 1):
			print("Checking mail. Attempt {} of {}".format(i, num_attempts))
			messages = mailbox.get_new_mail()
			msg_num, total_msgs = i, len(messages)
			for message in messages:
				try:
					_print_message_details(message)
					parsed_text = _extract_content(message)
					print("Parsed Text from message {} of {}:".format(msg_num, total_msgs))
					print_with_color(parsed_text, GREEN)
					msg_num += 1
					print("-------------")
					_process_message(message, parsed_text)
				except Exception as e:
					print_with_color("Failed to process email message num {}. Exception {}".format(msg_num, e), RED)
					get_traceback()
			print("Sleeping for {} seconds".format(args.check_frequency))
			time.sleep(args.check_frequency)
	except Exception as e:
		print_with_color("Failed to process messages. Exception {}".format(e), RED)
		get_traceback()


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Check mail and parse messages sent via reply-to \
									 conversation email functionality")
	parser.add_argument('--check_count', dest='num_times_to_check_mail', type=int,
						default=DEFAULT_NUM_MAIL_CHECKS, help='Num of times to check mail')
	parser.add_argument('--check_freq', dest='check_frequency', type=int,
						default=DEFAULT_MAIL_CHECK_FREQUENCY, help='secs between each mail check')
	args = parser.parse_args()
	main(args)
