import datetime

import utils

from flask_mongoengine import Document
from flask_mongoengine import DoesNotExist
from flask_mongoengine import MultipleObjectsReturned
from mongoengine.fields import StringField, BooleanField, DateTimeField, FloatField

# The User class is a model representing a CDC user
class User(Document):
    # DATABASE ENTRIES
    # username: The user's username
    username = StringField(max_length=512, required=True)
    # The user's social security number
    ssn = StringField(default=None)
    # wage: The user's hourly wage
    wage = StringField(default=None)
    # defines whether or not the user is an approver (overwritten at login)
    is_approver = BooleanField(default=False)
    # defines whether or not the user is an admin (overwritten at login)
    is_admin = BooleanField(default=False)

    # OBJECT METHODS
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    # Gets a user object by the username
    # CLASS METHOD
    @classmethod
    def get_user_by_username(cls, username):
        try:
            user = User.objects(username=username).get()
            return user
        except DoesNotExist, e:
            return False


class TimeRecord(Document):
    """
    A model representing a single day's time info.

    :param username: The username of who the TimeRecord is for.
    :param date: The date the TimeRecord represents.
    :param clock_in: The time representing when the employee clocked in for the day.
    :param clock_out: The time that the employee clocked out.
    :param approved: Records if a TimeRecord is approved by a payroll approver.
    :param approved_by: The username of the person who approved the TimeRecord.
    :param hours: The number of hours worked that day.
    """
    username = StringField(default=None, required=True)
    date = DateTimeField(default=datetime.date.today(), required=True)
    clock_in = DateTimeField(required=False)
    clock_out = DateTimeField(required=False)
    approved = BooleanField(default=False, required=True)
    approved_by = StringField(max_length=255, required=False)
    hours = FloatField()

    def set_hours(self):
        """
        Set the number of hours worked based on the clock_in and clock_out times.

        :returns: The number of hours worked if the TimeRecord contains a clock_in and
        clock_out, else returns None.
        """
        if not self.clock_in or not self.clock_out:
            return

        time_worked = self.clock_out - self.clock_in
        self.hours = time_worked.seconds / 3600.0
        return self.hours

    @classmethod
    def get_current_week(cls, username, today=datetime.date.today()):
        """
        Given a day, this will return a weeks worth of TimeRecords objects, starting with Monday,
        that contains the date passed in as today.

        :param username: The username to lookup
        :param today: The day to use to look up the week.  Defaults to today.
        :returns: A list of TimeRecord objects, for the username given, that is a payroll week
        containing the day given.
        """

        try:
            user = User.objects(username=username).get()
        except DoesNotExist, e:
            return

        last_monday = utils.get_last_monday(today)
        next_monday = last_monday + datetime.timedelta(days=7)
        records = TimeRecord.objects(date__gte=last_monday,
                                     date__lt=next_monday,
                                     username=username).order_by('date')
        if len(records) < 7:
            for day in xrange(7):
                date = last_monday + datetime.timedelta(days=day)
                try:
                    record = TimeRecord.objects(date=date, username=username).get()
                except DoesNotExist, e:
                    TimeRecord(date=date, username=username).save()
            records = TimeRecord.objects(date__gte=last_monday,
                                         date__lt=next_monday,
                                         username=username).order_by('date')

        return records

    @classmethod
    def get_approved_records_by_username(cls, username, num_days=None):
        """
        Gets a list of approved TimeRecords for a user.

        :param username: The user to lookup.
        :param num_days: An optional number of days to filter by.
        "returns: A list of all of the approved TimeRecords for that user.
        """
        if not num_days:
            return TimeRecord.objects(username=username,
                                      clock_in__exists=True,
                                      clock_out__exists=True,
                                      approved_by__exists=True)

        start_date = datetime.date.today() - datetime.timedelta(days=num_days)
        return TimeRecord.objects(username=username,
                                  clock_in__exists=True,
                                  clock_out__exists=True,
                                  date__gte=start_date,
                                  approved_by__exists=True)

    @classmethod
    def get_unapproved_records(cls):
        """
        Gets a list of all unapproved records on the system.

        :returns: A list of all TimeRecord objects that have a clock_in and a clock_out set
        but have not been approved yet.
        """
        return TimeRecord.objects(clock_in__exists=True,
                                  clock_out__exists=True,
                                  approved_by__exists=False)