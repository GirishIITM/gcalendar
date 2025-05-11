#!/usr/bin/env python3
# gcalendar is a tool to read Google Calendar events from your terminal.

# Copyright (C) 2020  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import json
import os
import sys
import subprocess
import logging
from datetime import datetime, timezone
from os.path import join

from dateutil.relativedelta import relativedelta
from googleapiclient.errors import HttpError
from httplib2 import HttpLib2Error
from oauth2client import client
from oauth2client import clientsecrets

from gcalendar import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, TOKEN_STORAGE_VERSION, VERSION
from gcalendar.gcalendar import GCalendar
from gcalendar.notification import notify_events

# the home folder
HOME_DIRECTORY = os.environ.get('HOME') or os.path.expanduser('~')

# ~/.config/gcalendar folder
CONFIG_DIRECTORY = os.path.join(os.environ.get(
    'XDG_CONFIG_HOME') or os.path.join(HOME_DIRECTORY, '.config'), 'gcalendar')

TOKEN_FILE_SUFFIX = "_" + TOKEN_STORAGE_VERSION + ".dat"


def validate_account_id(account_id):
    """
    Validate the argparse argument --account
    """
    account = str(account_id)
    if not account.isalnum():
        raise argparse.ArgumentTypeError("%s is not an alphanumeric id" % account)
    return account


def validate_since(date):
    """
    Validate the argparse argument --since
    """
    try:
        return datetime.strptime(date, "%Y-%m-%d").astimezone()
    except ValueError:
        raise argparse.ArgumentTypeError(date + " is not in %Y-%m-%d format")


def delete_if_exist(file_path):
    try:
        os.remove(file_path)
    except OSError:
        pass


def list_accounts():
    accounts = list()
    for file in os.listdir(CONFIG_DIRECTORY):
        if os.path.isfile(join(CONFIG_DIRECTORY, file)) and file.endswith(TOKEN_FILE_SUFFIX):
            accounts.append(file.replace(TOKEN_FILE_SUFFIX, ""))
    return accounts


def reset_account(account_id, storage_path):
    if os.path.exists(storage_path):
        delete_if_exist(storage_path)
        if os.path.exists(storage_path):
            return "Failed to reset %s" % account_id
        else:
            return "Successfully reset %s" % account_id
    else:
        return "Account %s does not exist" % account_id


def handle_error(error, message, output_type, debug_mode):
    if output_type == "txt":
        print("\033[91m" + message + "\033[0m")
    elif output_type == "json":
        print('{"error": "%s"}' % message)
    if debug_mode:
        raise error


def print_status(status, output_type):
    if output_type == "txt":
        print(status)
    elif output_type == "json":
        print('{"status": "%s"}' % status)


def print_list(obj_list, output_type):
    if output_type == "txt":
        for acc in obj_list:
            print(acc)
    elif output_type == "json":
        print(json.dumps(obj_list))


def print_events(events, output_type):
    if output_type == "txt":
        for event in events:
            print("%s:%s - %s:%s\t%s\t%s\t%s" % (
                event["start_date"], event["start_time"], event["end_date"], event["end_time"], event["summary"],
                event["location"], event["status"]))
    elif output_type == "json":
        print(json.dumps(events))


def handle_exception(client_id, client_secret, account_id, storage_path, output, debug, function):
    failed = False
    try:
        g_calendar = GCalendar(client_id, client_secret, account_id, storage_path)
        return failed, function(g_calendar)

    except clientsecrets.InvalidClientSecretsError as ex:
        handle_error(ex, "Invalid Client Secrets", output, debug)
        failed = True

    except client.AccessTokenRefreshError as ex:
        handle_error(ex, "Failed to refresh access token", output, debug)
        failed = True

    except HttpLib2Error as ex:
        if "Unable to find the server at" in str(ex):
            msg = "Unable to find the Google Calendar server. Please check your connection."
        else:
            msg = "Failed to connect Google Calendar"
        handle_error(ex, msg, output, debug)
        failed = True

    except HttpError as ex:
        if "Too Many Requests" in str(ex):
            msg = "You have reached your request quota limit. Please try gcalendar after a few minutes."
        else:
            msg = "Failed to connect Google Calendar"

        handle_error(ex, msg, output, debug)
        failed = True

    except BaseException as ex:
        handle_error(ex, "Failed to connect Google Calendar", output, debug)
        failed = True
    return failed, None


def setup_crontab(interval, notify_minutes, account, calendars, debug):
    """Setup or update a crontab entry for calendar notifications"""
    # Get the current user's crontab
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout
    except subprocess.CalledProcessError:
        # No existing crontab
        current_crontab = ""
    
    # Check if our cronjob is already there
    gcal_job_prefix = "# GCalendar notification job"
    if gcal_job_prefix in current_crontab:
        print("Existing gcalendar crontab entry found. Updating...")
        # Remove existing GCalendar crontab entries
        new_lines = []
        skip_line = False
        for line in current_crontab.splitlines():
            if line.startswith(gcal_job_prefix):
                skip_line = True
                continue
            if skip_line and line.strip() and not line.startswith('#'):
                skip_line = False
            if not skip_line:
                new_lines.append(line)
        
        current_crontab = "\n".join(new_lines)
    
    # Build the calendar argument string
    calendar_arg = " ".join([f'"{cal}"' for cal in calendars]) if calendars != ["*"] else "*"
    
    # Build the command with all options
    notify_cmd = f"gcalendar-notify --notify {notify_minutes} --account {account}"
    if calendar_arg != "*":
        notify_cmd += f" --calendar {calendar_arg}"
    if debug:
        notify_cmd += " --debug"
    
    # Add the new cronjob
    new_crontab = current_crontab.rstrip() + f"\n\n{gcal_job_prefix}\n*/{interval} * * * * {notify_cmd}\n"
    
    # Write to a temporary file
    temp_crontab = os.path.join(HOME_DIRECTORY, ".gcalendar_crontab_temp")
    with open(temp_crontab, "w") as f:
        f.write(new_crontab)
    
    # Install the new crontab
    try:
        subprocess.run(['crontab', temp_crontab], check=True)
        print(f"Successfully set up crontab to check every {interval} minutes for upcoming events")
        print(f"Will notify you {notify_minutes} minutes before each event")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set up crontab: {e}")
    
    # Clean up
    os.remove(temp_crontab)


def remove_crontab():
    """Remove gcalendar crontab entries"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout
        
        if "# GCalendar notification job" not in current_crontab:
            print("No gcalendar crontab entry found")
            return
        
        # Remove GCalendar crontab entries
        new_lines = []
        skip_line = False
        for line in current_crontab.splitlines():
            if line.startswith("# GCalendar notification job"):
                skip_line = True
                continue
            if skip_line and line.strip() and not line.startswith('#'):
                skip_line = False
            if not skip_line:
                new_lines.append(line)
        
        new_crontab = "\n".join(new_lines)
        
        # Write to a temporary file
        temp_crontab = os.path.join(HOME_DIRECTORY, ".gcalendar_crontab_temp")
        with open(temp_crontab, "w") as f:
            f.write(new_crontab)
        
        # Install the new crontab
        subprocess.run(['crontab', temp_crontab], check=True)
        print("Successfully removed gcalendar crontab entry")
        
        # Clean up
        os.remove(temp_crontab)
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to remove crontab: {e}")


def process_request(account_ids, args):
    client_id = args.client_id
    client_secret = args.client_secret
    if not client_id or not client_secret:
        client_id = DEFAULT_CLIENT_ID
        client_secret = DEFAULT_CLIENT_SECRET

    if args.list_accounts:
        # --list-accounts
        print_list(list_accounts(), args.output)
        return 0
    elif args.reset:
        # --reset
        for account_id in account_ids:
            storage_path = join(CONFIG_DIRECTORY, account_id + TOKEN_FILE_SUFFIX)
            status = reset_account(account_id, storage_path)
            print_status(status, args.output)
        return 0

    elif args.status:
        # --status
        for account_id in account_ids:
            storage_path = join(CONFIG_DIRECTORY, account_id + TOKEN_FILE_SUFFIX)
            if os.path.exists(storage_path):
                if GCalendar.is_authorized(storage_path):
                    status = "Authorized"
                else:
                    status = "Token Expired"
            else:
                status = "Not authenticated"
            print_status(status, args.output)
        return 0

    elif args.list_calendars:
        # --list-calendars
        calendars = []
        for account_id in account_ids:
            storage_path = join(CONFIG_DIRECTORY, account_id + TOKEN_FILE_SUFFIX)
            failed, result = handle_exception(client_id, client_secret, account_id, storage_path, args.output,
                                              args.debug,
                                              lambda cal: cal.list_calendars())
            if failed:
                return -1
            else:
                calendars.extend(result)
        print_list(calendars, args.output)
    elif args.setup_cron is not None:
        # Handle crontab setup
        interval = args.setup_cron
        notify_mins = int(args.notify) if args.notify else 15

        if interval <= 0:
            print("Error: Cron interval must be greater than 0")
            return 1

        for account_id in account_ids:
            setup_crontab(
                interval,
                notify_mins,
                account_id,
                args.calendar,
                args.debug
            )
        return 0
    elif args.remove_cron:
        # Remove the crontab entry
        remove_crontab()
        return 0
    else:
        # List events
        no_of_days = int(args.no_of_days)
        selected_calendars = [x.lower() for x in args.calendar]
        since = args.since
        current_time = datetime.now(timezone.utc).astimezone()
        time_zone = current_time.tzinfo
        if since is None:
            since = current_time
        start_time = str(since.isoformat())
        end_time = str((since + relativedelta(days=no_of_days)).isoformat())
        events = []
        for account_id in account_ids:
            storage_path = join(CONFIG_DIRECTORY, account_id + TOKEN_FILE_SUFFIX)
            failed, result = handle_exception(client_id, client_secret, account_id, storage_path, args.output,
                                              args.debug,
                                              lambda cal: cal.list_events(selected_calendars, start_time, end_time,
                                                                          time_zone))
            if failed:
                return -1
            else:
                events.extend(result)
        events = sorted(events, key=lambda event: event["start_date"] + event["start_time"])
        
        # Handle notifications if requested
        if args.notify:
            notify_minutes = int(args.notify)
            notify_events(events, notify_minutes)
            
        print_events(events, args.output)


def main():
    """
    Retrieve Google Calendar events.
    """
    parser = argparse.ArgumentParser(prog='gcalendar', description="Read your Google Calendar events from terminal.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list-calendars", action="store_true", help="list all calendars from the Google account")
    group.add_argument("--list-accounts", action="store_true", help="list the id of gcalendar accounts")
    group.add_argument("--status", action="store_true", help="print the status of the gcalendar account")
    group.add_argument("--reset", action="store_true", help="reset the account")
    group.add_argument("--setup-cron", type=int, metavar="INTERVAL", help="setup crontab to check every INTERVAL minutes")
    group.add_argument("--remove-cron", action="store_true", help="remove gcalendar crontab entry")
    
    parser.add_argument("--calendar", type=str, default=["*"], nargs="*", help="calendars to list events from")
    parser.add_argument("--since", type=validate_since, help="number of days to include")
    parser.add_argument("--no-of-days", type=str, default="7", help="number of days to include")
    parser.add_argument("--account", type=validate_account_id, default=["default"], nargs="*",
                        help="an alphanumeric name to uniquely identify the account")
    parser.add_argument("--output", choices=["txt", "json"], default="txt", help="output format")
    parser.add_argument("--client-id", type=str, help="the Google client id")
    parser.add_argument("--client-secret", type=str,
                        help="the Google client secret")
    parser.add_argument("--notify", type=str, help="send notification before event (minutes)")
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    parser.add_argument("--debug", action="store_true", help="run gcalendar in debug mode")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    # Create the config folder if not exists
    if not os.path.exists(CONFIG_DIRECTORY):
        os.mkdir(CONFIG_DIRECTORY)

    return process_request(args.account, args)


if __name__ == "__main__":
    sys.exit(main())
