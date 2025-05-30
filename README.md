# gcalendar

[![PyPI version](https://badge.fury.io/py/gcalendar.svg)](https://badge.fury.io/py/gcalendar)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/slgobinath)

A command-line tool to read your Google Calendar events in JSON format.

## Installation

### Ubuntu, Linux Mint and other Ubuntu Derivatives

```shell script
sudo add-apt-repository ppa:slgobinath/gcalendar
sudo apt update
sudo apt install gcalendar
```

### Arch

```shell script
yay -S gcalendar
```

OR

```shell script
packer -S gcalendar
```

### Other Distributions

Install these dependencies:
```shell script
python3-pip python3-setuptools python3-dateutil python3-oauth2client python3-googleapi
```

Install `gcalendar`:
```shell script
pip3 install gcalendar
````

### Install from Source
```shell script
sudo apt install python3-pip python3-setuptools python3-dateutil python3-oauth2client python3-googleapi git
git clone https://github.com/slgobinath/gcalendar.git
cd gcalendar
pip3 install -e .
```

## Run from Source

```shell script
sudo apt install python3-pip python3-setuptools python3-dateutil python3-oauth2client python3-googleapi git
git clone https://github.com/slgobinath/gcalendar.git
cd gcalendar
python3 -m gcalendar
```

## Help

```text
usage: gcalendar [-h] [--list-calendars | --list-accounts | --status | --reset | --setup-cron INTERVAL | --remove-cron] [--calendar [CALENDAR [CALENDAR ...]]] [--no-of-days NO_OF_DAYS] [--account ACCOUNT]
                 [--output {txt,json}] [--client-id CLIENT_ID] [--client-secret CLIENT_SECRET] [--notify NOTIFY] [--version] [--debug]

Read your Google Calendar events from terminal.

optional arguments:
  -h, --help            show this help message and exit
  --list-calendars      list all calendars from the Google account
  --list-accounts       list the id of gcalendar accounts
  --status              print the status of the gcalendar account
  --reset               reset the account
  --setup-cron INTERVAL setup crontab to check every INTERVAL minutes
  --remove-cron         remove gcalendar crontab entry
  --calendar [CALENDAR [CALENDAR ...]]
                        calendars to list events from
  --no-of-days NO_OF_DAYS
                        number of days to include
  --account ACCOUNT     an alphanumeric name to uniquely identify the account
  --output {txt,json}   output format
  --client-id CLIENT_ID
                        the Google client id
  --client-secret CLIENT_SECRET
                        the Google client secret
  --notify NOTIFY       send notification before event (minutes)
  --version             show program's version number and exit
  --debug               run gcalendar in debug mode
```

## Authorization

Run `gcalendar` from the terminal. It will open the Google Calendar OAuth screen in your default browser.
Allow gcalendar to view your calendars as shown in this video: [gcalendar Authorization](https://www.youtube.com/watch?v=mwU8AQmzIPE).

After successful authorization, `gcalendar` should print calendar events on your terminal.

## Usage

### List Calendars

```shell script
gcalendar --list-calendar
```

### List Events

```shell script
# list next 7 days events
gcalendar

# list next 30 days events
gcalendar --no-of-days 30

# list events from selected calendar
gcalendar --calendar "Holidays in Canada"
```

### Separate Accounts

```shell script
# the default account
gcalendar

# different account named foo
gcalendar --account foo

# different account named bar
gcalendar --account bar
```

### Reset Accounts
```shell script
# reset the default account
gcalendar --reset

# reset the account named foo
gcalendar --account foo --reset

# reset the account named bar
gcalendar --account bar --reset
```

### Desktop Notifications

```shell script
# Get desktop notifications for events starting in the next 15 minutes
gcalendar --notify 15

# Get desktop notifications for events starting in the next 30 minutes
gcalendar --notify 30
```

### Automated Notifications with Cron

gcalendar can automatically check for upcoming events and send notifications:

```shell script
# Setup cron to check every 5 minutes and notify 15 minutes before events
gcalendar --setup-cron 5 --notify 15

# Setup cron to check every 10 minutes and notify 30 minutes before events
gcalendar --setup-cron 10 --notify 30

# Setup cron for a specific account and calendar
gcalendar --setup-cron 5 --notify 15 --account work --calendar "Meeting Calendar" "Important Dates"

# Remove gcalendar from crontab
gcalendar --remove-cron
```

The cron job will run in the background and send desktop notifications when events are approaching.

## Issues

Run `gcalendar --debug` and create an [issue](https://github.com/slgobinath/gcalendar/issues) with the output.

## Applications

Cinnamon [Google Calendar](https://cinnamon-spices.linuxmint.com/desklets/view/35) desklet uses `gcalendar` to pull calendar events and show them on Cinnamon desktop.

## License

GNU General Public License v3
