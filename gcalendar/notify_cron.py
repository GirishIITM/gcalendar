#!/usr/bin/env python3
# gcalendar is a tool to read Google Calendar events from your terminal.

# Copyright (C) 2023  Gobinath

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

import os
import sys
import logging
import argparse
from datetime import datetime, timezone, timedelta
from os.path import join

from dateutil.relativedelta import relativedelta
from oauth2client import client
from oauth2client import clientsecrets

# Ensure we can import from parent package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gcalendar import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, TOKEN_STORAGE_VERSION
from gcalendar.gcalendar import GCalendar
from gcalendar.notification import notify_events

# The home folder
HOME_DIRECTORY = os.environ.get('HOME') or os.path.expanduser('~')

# ~/.config/gcalendar folder
CONFIG_DIRECTORY = os.path.join(os.environ.get(
    'XDG_CONFIG_HOME') or os.path.join(HOME_DIRECTORY, '.config'), 'gcalendar')

# Ensure DISPLAY environment variable is set for notify-send
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':0'

# For notifications to work in cron
if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
    try:
        # Try to get the user's dbus session
        user_id = os.getuid()
        bus_file_path = f"/run/user/{user_id}/bus"
        if os.path.exists(bus_file_path):
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path={bus_file_path}"
    except Exception:
        # Fallback to a common default
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/1000/bus'

TOKEN_FILE_SUFFIX = "_" + TOKEN_STORAGE_VERSION + ".dat"

def setup_logging(debug_mode):
    """Set up logging configuration"""
    log_dir = os.path.join(HOME_DIRECTORY, '.local/share/gcalendar')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'notifier.log')
    
    level = logging.DEBUG if debug_mode else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_events(account_id, client_id, client_secret, calendars, days, minutes):
    """Get events from calendar"""
    try:
        storage_path = join(CONFIG_DIRECTORY, account_id + TOKEN_FILE_SUFFIX)
        if not os.path.exists(storage_path):
            logging.error(f"Account {account_id} is not authenticated. Run 'gcalendar' first.")
            return []
        
        # Setup time range - look from now until specified minutes in the future
        current_time = datetime.now(timezone.utc).astimezone()
        time_zone = current_time.tzinfo
        
        # For checking events, we need to look ahead by days
        start_time = str(current_time.isoformat())
        end_time = str((current_time + relativedelta(days=days)).isoformat())
        
        logging.debug(f"Checking for events between {start_time} and {end_time}")
        
        g_calendar = GCalendar(client_id, client_secret, account_id, storage_path)
        events = g_calendar.list_events(calendars, start_time, end_time, time_zone)
        return events
        
    except client.AccessTokenRefreshError:
        logging.error(f"Failed to refresh access token for account {account_id}. Try running 'gcalendar --reset --account {account_id}'")
    except clientsecrets.InvalidClientSecretsError:
        logging.error("Invalid client secrets")
    except Exception as e:
        logging.error(f"Error retrieving events: {e}")
    
    return []

def main():
    """Main function for the cron job notification script"""
    parser = argparse.ArgumentParser(description="GCalendar notification cron job")
    parser.add_argument("--account", type=str, default="default", help="account ID")
    parser.add_argument("--notify", type=int, default=15, help="minutes before event to notify")
    parser.add_argument("--days", type=int, default=1, help="days to look ahead for events")
    parser.add_argument("--calendar", type=str, default=["*"], nargs="*", help="specific calendars to check")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.debug)
    
    # Log the beginning of the run with timestamp
    logging.info(f"Starting notification check for account {args.account}")
    
    # Get calendar events
    events = get_events(
        args.account,
        DEFAULT_CLIENT_ID, 
        DEFAULT_CLIENT_SECRET,
        [cal.lower() for cal in args.calendar], 
        args.days,
        args.notify
    )
    
    if events:
        logging.info(f"Found {len(events)} events in the next {args.days} days")
        # Send notifications for events within the notification window
        notify_events(events, args.notify)
    else:
        logging.info("No events found")
    
    logging.info("Notification check complete")

if __name__ == "__main__":
    main()
