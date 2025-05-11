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

import subprocess
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# File to track already notified events to prevent duplicates
NOTIFIED_EVENTS_FILE = os.path.join(
    os.environ.get('XDG_DATA_HOME') or os.path.join(os.environ.get('HOME') or os.path.expanduser('~'), '.local/share'),
    'gcalendar/notified_events.json'
)

def notify_events(events, notify_minutes):
    """
    Check upcoming events and send notifications for those starting soon
    
    Args:
        events: List of calendar events
        notify_minutes: Minutes before an event to send notification
    """
    now = datetime.now()
    notification_window = now + timedelta(minutes=notify_minutes)
    
    # Load previously notified events
    notified_events = load_notified_events()
    
    # Filter events that start within the notification window
    upcoming_events = []
    for event in events:
        try:
            # Handle events with specific times (not all-day events)
            if event["start_time"] != "00:00" or event["end_time"] != "00:00":
                start_datetime_str = f"{event['start_date']} {event['start_time']}"
                start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
                
                # Check if event starts between now and notification window
                if now <= start_datetime <= notification_window:
                    # Create a unique ID for the event to prevent duplicate notifications
                    event_id = f"{event.get('summary', 'Unnamed')}-{start_datetime_str}"
                    
                    # Only add if we haven't notified about this event already
                    if event_id not in notified_events:
                        upcoming_events.append(event)
                        notified_events[event_id] = datetime.now().isoformat()
        except (ValueError, KeyError) as e:
            logging.warning(f"Error processing event for notification: {e}")
            continue
    
    # Send notifications for upcoming events
    for event in upcoming_events:
        send_notification(event)
    
    # Clean up old notified events (keep only events from the last 24 hours)
    clean_notified_events(notified_events)
    
    # Save updated notified events
    save_notified_events(notified_events)

def send_notification(event):
    """
    Send desktop notification for an event
    
    Args:
        event: Calendar event details
    """
    summary = event.get("summary", "Unnamed event")
    location = event.get("location", "")
    start_time = event.get("start_time", "")
    start_date = event.get("start_date", "")
    description = event.get("description", "")
    
    # Create notification message
    title = f"Upcoming Calendar Event: {summary}"
    message_parts = []
    
    message_parts.append(f"Date: {start_date}")
    message_parts.append(f"Time: {start_time}")
    
    if location:
        message_parts.append(f"Location: {location}")
    
    if description:
        # Truncate description if it's too long
        short_desc = description[:100] + "..." if len(description) > 100 else description
        message_parts.append(f"Details: {short_desc}")
    
    message = "\n".join(message_parts)
    
    try:
        # Use notify-send to display desktop notification
        # Set a longer timeout (10 seconds = 10000 ms)
        subprocess.call([
            'notify-send',
            '--icon=appointment',
            '--urgency=normal',
            '--expire-time=10000',
            title,
            message
        ])
        logging.debug(f"Notification sent for event: {summary}")
        return True
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")
        return False

def load_notified_events():
    """Load previously notified events from file"""
    try:
        if os.path.exists(NOTIFIED_EVENTS_FILE):
            with open(NOTIFIED_EVENTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Error loading notified events: {e}")
    return {}

def save_notified_events(notified_events):
    """Save notified events to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(NOTIFIED_EVENTS_FILE), exist_ok=True)
        with open(NOTIFIED_EVENTS_FILE, 'w') as f:
            json.dump(notified_events, f)
    except Exception as e:
        logging.warning(f"Error saving notified events: {e}")

def clean_notified_events(notified_events):
    """Remove old events from the notified events dict"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    to_remove = []
    
    for event_id, timestamp_str in notified_events.items():
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp < cutoff_time:
                to_remove.append(event_id)
        except (ValueError, TypeError):
            to_remove.append(event_id)
    
    for event_id in to_remove:
        notified_events.pop(event_id, None)
