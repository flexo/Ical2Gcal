import sys
import getopt
import re
import urllib
import string
import time
try:
  from xml.etree import ElementTree # for Python 2.5 users
except ImportError:
  from elementtree import ElementTree

import gdata.calendar.service
import gdata.service
import atom.service
import gdata.calendar
import atom

from configobj import ConfigObj
import icalendar # http://codespeak.net/icalendar/

# Outlook puts a space where it shouldn't in 'third tuesday of the month'
# lines (eg, '3 TU' rather than '3TU')
WEEKDAY_RULE = re.compile('(?P<signal>[+-]?)(?P<relative>[\d]?)'
                          ' ?(?P<weekday>[\w]{2})$')
icalendar.prop.WEEKDAY_RULE = WEEKDAY_RULE

GOOGLE_STRFTIME = '%Y-%m-%dT%H:%M:%S.000Z'

def cals(client):
    feed = client.GetAllCalendarsFeed()
    for cal in feed.entry:
        yield (cal.content.src, cal.title.text)

class Event(object):
    def __init__(self):
        self.uid = None
        self.start = None
        self.end = None
        self.subject = None
        self.description = None
        self.location = None
        self.recurrence = None

    def __repr__(self):
        s = "[Event"
        for attr in ('uid', 'start', 'end', 'subject', 'description', 'location', 'recurrence'):
            s += (' ' + attr + '=' + repr(getattr(self, attr)))
        s += "]"
        return s

def make_events(s):
    """Extract events from an .ics file's text."""
    cal = icalendar.Calendar.from_string(s)
    events = []
    for subcomponent in cal.subcomponents:
        if isinstance(subcomponent, icalendar.Timezone):
            pass # TODO - handle this?
        elif isinstance(subcomponent, icalendar.Event):
            event = Event()
            event.uid = subcomponent.decoded('uid')
            # TODO - handle timezone of dtstart TZID param
            event.start = subcomponent.decoded('dtstart')
            event.end = subcomponent.decoded('dtend') # TODO - handle 'duration'
            event.subject = subcomponent.decoded('summary')
            event.description = subcomponent.decoded('description')
            event.location = subcomponent.decoded('location')
            if 'rrule' in subcomponent:
                # Fix Outlook's trigger-happy spacebar finger:
                for k in subcomponent['rrule']:
                    for i in range(len(subcomponent['rrule'][k])):
                        if isinstance(subcomponent['rrule'][k][i], basestring):
                            subcomponent['rrule'][k][i] = subcomponent['rrule'][k][i].replace(' ', '')
                event.recurrence = (
                    'DTSTART:' + subcomponent['dtstart'].ical() + '\r\n' +
                    'DTEND:' + subcomponent['dtend'].ical() + '\r\n' +
                    'RRULE:' + subcomponent['rrule'].ical())
            events.append(event)
    return events

def send_events(client, api_url, events):
    """Send events to Google Calendar.
    
    client - a CalendarService object
    api_url - the URL to send events to
    events - a list of Event objects
    """
    for event in events:
        # TODO - we need to check whether to insert or update an existing entry
        gevent = gdata.calendar.CalendarEventEntry()
        gevent.title = atom.Title(text=event.subject)
        gevent.content = atom.Content(text=event.description)
        gevent.where.append(gdata.calendar.Where(value_string=event.location))
        if event.recurrence:
            gevent.recurrence = gdata.calendar.Recurrence(text=event.recurrence)
        else:
            gevent.when.append(gdata.calendar.When(
                start_time=event.start.strftime(GOOGLE_STRFTIME),
                end_time=event.end.strftime(GOOGLE_STRFTIME)))
        
        print "sending new event (%s%s) to %s" % (
            event.start.strftime('%Y-%m-%d %H:%M'),
            event.recurrence and ' recurring' or '',
            api_url)
        try:
            new_event = client.InsertEvent(gevent, api_url)
        except gdata.service.RequestError, e:
            # Google sometimes barfs
            new_event = client.InsertEvent(gevent, api_url)

        # TODO - save our ID <-> google ID mapping

def make_client(email, password):
    """Return a CalendarService set up with this email and password"""
    cal_client = gdata.calendar.service.CalendarService()
    cal_client.email = email
    cal_client.password = password
    cal_client.source = 'Mailbox2GCal'
    cal_client.ProgrammaticLogin()
    return cal_client

def usage():
    return """Usage: %s [options] <config>

Options:
    -l, --listcals  List available calendars for the account, then exit
    -i, --ical      Process the file given. Use - for stdin.

One and only one of -l and i must be provided.
""" % sys.argv[0]

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "hli:", ["help", "listcals", "--ical"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print >> sys.stderr, str(err) # will print something like "option -a not recognized"
        print >> sys.stderr, usage()
        return 2
    listcals = False
    ical_filename = None
    for o, a in opts:
        if o in ("-h", "--help"):
            print usage()
            sys.exit()
        elif o in ("-l", "--listcals"):
            listcals = True
        elif o in ('-i', '--ical'):
            ical_filename = a
        else:
            assert False, "unhandled option"
    try:
        cfgfilename = args[0]
    except IndexError:
        print >> sys.stderr, usage()
        return 2
    if not (listcals or ical_filename):
        print >> sys.stderr, "One of -l or -i must be provided."
        print >> sys.stderr, usage()
    if listcals and ical_filename:
        print >> sys.stderr, "-l and -i are mutually exclusive."
        print >> sys.stderr, usage()

    config = ConfigObj(cfgfilename)

    email = config['account']['email']
    password = config['account']['password']
    client = make_client(email, password)
    
    if listcals:
        print '\n'.join(repr(t) for t in cals(client))
        return 0

    # Make sure to fetch the calendar details of the config file after -l has
    # been processed to allow new users to list calendars before writing the
    # config
    cal_url = config['calendar']['api_url']

    if ical_filename == '-':
        ical_file = sys.stdin
    else:
        ical_file = open(ical_filename, 'rb')
    events = make_events(ical_file.read())
    send_events(client, cal_url, events)

if __name__ == '__main__':
    sys.exit(main())
