#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

plt.style.use(os.path.join(os.path.dirname(__file__), 'mplstyle'))

def system_timezone_info():
    return datetime.now(timezone.utc).astimezone().tzinfo

def plot(t, data_frame, column_name, tz, args):
    fig = plt.figure(figsize = (args.width, args.height), dpi = args.dpi)
    ax = fig.add_subplot(1, 1, 1)

    thermal_match_result = re.match(r'thermal tz([0-9]+)', column_name)

    if thermal_match_result:
        ax.plot(t, data_frame[column_name] * 1e-3)
        ax.set_ylabel('Temperature [$^\circ$C]')
        ax.set_title(f'Thermal Zone {thermal_match_result.group(1)}')
    else:
        ax.plot(t, data_frame[column_name])
        ax.set_ylabel(column_name)

    datetime_formatter = mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
    datetime_formatter.set_tzinfo(tz)
    ax.xaxis.set_major_formatter(datetime_formatter)
    ax.set_xlabel(f'Date & Time ({t[0].tzinfo})')

    x_min = args.start_time if args.start_time else t[0]
    x_max = args.end_time if args.end_time else t[-1]
    ax.set_xlim(x_min, x_max)
    
    return fig

def is_column_for_cpu_usage(column_name):
    cpu_ids = ['total'] + list(range(128))
    suffixes = ['usr', 'sys', 'idl', 'wai', 'stl']

    for cpu_id in cpu_ids:
        if cpu_id == 'total':
            prefix = 'total cpu usage:'
        else:
            prefix = f'cpu{cpu_id} usage:'

        for suffix in suffixes:
            if column_name == f'{prefix}{suffix}':
                return True
    return False

def has_columns_for_cpu_usage_plot(data_frame, cpu_id):
    columns = data_frame.columns

    if cpu_id == 'total':
        prefix = 'total cpu usage:'
    else:
        prefix = f'cpu{cpu_id} usage:'

    required_suffixes = ['usr', 'sys', 'idl', 'wai', 'stl']
    required_columns  = [f'{prefix}{suffix}' for suffix in required_suffixes]
    return all([required_column in columns for required_column in required_columns])

def cpu_usage_plot(t, data_frame, cpu_id, tz, args):
    fig = plt.figure(figsize = (args.width, args.height), dpi = args.dpi)
    ax = fig.add_subplot(1, 1, 1)

    if cpu_id == 'total':
        column_name_prefix = 'total cpu usage:'
        title = 'CPU Total'
    else:
        column_name_prefix = f'cpu{cpu_id} usage:'
        title = f'CPU #{cpu_id}'

    label_sets = [ ('usr', 'User'),
                   ('sys', 'System'),
                   ('stl', 'Steal'),
                   ('wai', 'IO Wait'),
                   ('idl', 'Idle') ]
    short_labels = [short_label for short_label, long_label in label_sets]
    long_labels  = [long_label  for short_label, long_label in label_sets]
    column_names = [f'{column_name_prefix}{short_label}' for short_label in short_labels]
    
    ax.stackplot(t,
                 data_frame[column_names[0]],
                 data_frame[column_names[1]],
                 data_frame[column_names[2]],
                 data_frame[column_names[3]],
                 data_frame[column_names[4]],
                 labels = long_labels)
    ax.set_title(title)
    ax.set_xlabel(f'Date & Time ({t[0].tzinfo})')
    ax.set_ylim(0, 100)
    ax.set_yticks((0, 20, 40, 60, 80, 100))
    ax.set_yticklabels(('0 %', '20 %', '40 %', '60 %', '80 %', '100 %'))

    datetime_formatter = mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
    datetime_formatter.set_tzinfo(tz)
    ax.xaxis.set_major_formatter(datetime_formatter)

    x_min = args.start_time if args.start_time else t[0]
    x_max = args.end_time if args.end_time else t[-1]
    ax.set_xlim(x_min, x_max)

    ax.legend()
    
    return fig

def to_filename_base(column_name):
    characters_to_replace = [' ', ':', '/']
    for c in characters_to_replace:
        column_name = column_name.replace(c, '_')
    return column_name

def extract_column_names(dstat_file):
    data_frame = pd.read_csv(dstat_file, header=[4,5], nrows=0)
    column_names = []

    previous_category = ''
    for column in data_frame.columns:
        if column[0].startswith('Unnamed: '):
            category = previous_category
        else:
            category = column[0]
            previous_category = category

        if column[1].startswith(category):
            column_name = column[1]
        else:
            column_name = f'{category} {column[1]}'
            
        column_names.append(column_name)

    return column_names

def datetime_type(iso_format):
    try:
        return datetime.fromisoformat(iso_format)
    except ValueError as e:
        msg =  ' Time must be in ISO 8601 format.'
        msg += ' See https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat for more details.'
        raise argparse.ArgumentTypeError(str(e) + msg)

def is_aware(d):
    return (d.tzinfo is not None) and (d.tzinfo.utcoffset(d) is not None)

def parse_argments():
    description = '''
Generate time series plots from the dstat output file.
This tool assumes that the file is generated by 0.8.0.
'''
    parser = argparse.ArgumentParser(description = description)
    
    parser.add_argument('--output-dir',
                        dest    = 'output_dir',
                        metavar = 'DIR',
                        default = 'output',
                        help    = 'Time series plots will be generated under this directory. (default: %(default)s)')
    parser.add_argument('--utc',
                        action  = 'store_true',
                        help    = f'Use UTC to display the time instead of the time zone setting of your system ({system_timezone_info()}).')
    parser.add_argument('--width',
                        dest    = 'width',
                        metavar = 'WIDTH',
                        default = plt.rcParams.get('figure.figsize')[0],
                        help    = 'Width of plot in inches. (default: %(default)s)')
    parser.add_argument('--height',
                        dest    = 'height',
                        metavar = 'HEIGHT',
                        default = plt.rcParams.get('figure.figsize')[1],
                        help    = 'Height of plot in inches. (default: %(default)s)')
    parser.add_argument('--dpi',
                        dest    = 'dpi',
                        metavar = 'DPI',
                        default = plt.rcParams.get('figure.dpi'),
                        help    = 'DPI for plotting. (default: %(default)s)')
    parser.add_argument('--start-time',
                        dest    = 'start_time',
                        type    = datetime_type,
                        default = None,
                        help    = 'Plot the data recorded only after the specified time.')
    parser.add_argument('--end-time',
                        dest    = 'end_time',
                        type    = datetime_type,
                        default = None,
                        help    = 'Plot the data recorded only before the specified time.')
    parser.add_argument('--image-format',
                        dest    = 'image_format',
                        metavar = 'FORMAT',
                        default = 'png',
                        help    = 'Image format. (default: %(default)s)')
    parser.add_argument('--show-plot',
                        dest    = 'show_plot',
                        action  = 'store_true',
                        help    = 'Show plots in GUI.')
    parser.add_argument('dstat_file',
                        metavar = 'INPUT',
                        help    = 'File generated by dstat --output option.')
    
    return parser.parse_args()

def main():
    args = parse_argments()

    output_dir = Path(args.output_dir)
    column_names = extract_column_names(args.dstat_file)

    data_frame = pd.read_csv(
        args.dstat_file,
        header = 5,
        names = column_names,
    )
       
    # Data for X axis (time)
    if 'epoch' in data_frame.columns:
        tz = timezone.utc if args.utc else system_timezone_info()
        t = [datetime.fromtimestamp(epoch, tz) for epoch in data_frame['epoch']]
        
        start_i = 0
        if args.start_time:
            start_time = args.start_time
            if not is_aware(start_time):
                start_time = start_time.replace(tzinfo = tz)

            try:
                start_i = next(i for i, tt in enumerate(t) if tt >= start_time)
            except:
                print(f'No data after {start_time}.')
                exit(1)

        end_i = -1
        if args.end_time:
            end_time = args.end_time
            if not is_aware(end_time):
                end_time = end_time.replace(tzinfo = tz)

            try:
                end_i = max(i for i, tt in enumerate(t) if tt <= end_time)
            except:
                print(f'No data before {end_time}.')
                exit(1)

        t = t[start_i:end_i]
        data_frame = data_frame[start_i:end_i]
    else:
        # TODO: treat 'time' column as the timestamp if 'epoch' column does not exist.
        t = np.arange(0, len(data_frame))

    # Plot individual metrics.
    for column_name in data_frame.columns:
        if column_name == 'system time' or column_name == 'epoch':
            continue

        if is_column_for_cpu_usage(column_name):
            continue

        fig = plot(t, data_frame, column_name, tz, args)
        
        output_filename = '.'.join((to_filename_base(column_name), args.image_format))
        output_path = output_dir / output_filename
        output_dir.mkdir(parents = True, exist_ok = True)
        fig.savefig(output_path)
        print(f'Generated a plot as {output_path}')

        if not args.show_plot:
            plt.close(fig)

    # Plot CPU utility rate.
    cpu_ids = ['total'] + list(range(128))
    for cpu_id in cpu_ids:
        if not has_columns_for_cpu_usage_plot(data_frame, cpu_id):
            continue
        
        fig = cpu_usage_plot(t, data_frame, cpu_id, tz, args)
        if cpu_id == 'total':
            filename_base = 'total_cpu_usage'
        else:
            filename_base = f'cpu{cpu_id}_usage'
            
        output_filename = '.'.join((filename_base, args.image_format))
        output_path = output_dir / output_filename
        output_dir.mkdir(parents = True, exist_ok = True)
        fig.savefig(output_path)
        print(f'Generated a plot as {output_path}')

    if args.show_plot:
        plt.show()
    
if __name__ == "__main__":
    main()
