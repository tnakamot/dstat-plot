#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
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
    ax.plot(t, data_frame[column_name])
    ax.set_xlabel(f'Date & Time ({t[0].tzinfo})')
    ax.set_ylabel(column_name)

    datetime_formatter = mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
    datetime_formatter.set_tzinfo(tz)
    ax.xaxis.set_major_formatter(datetime_formatter)

    if column_name.startswith('cpu'):
        ax.set_ylim(0, 100)
        ax.set_yticks((0, 20, 40, 60, 80, 100))
    
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

def parse_argments():
    description = '''
Generate time series plots from the dstat output file.
This tool assumes that the file is generated by 0.8.0.
'''
    parser = argparse.ArgumentParser(
        description = description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--output-dir',
                        dest    = 'output_dir',
                        metavar = 'DIR',
                        default = 'output',
                        help    = 'Time series plots will be generated under this directory.')
    parser.add_argument('--utc',
                        action  = 'store_true',
                        help    = f'Use UTC to display the time instead of the time zone setting of your system ({system_timezone_info()}).')
    parser.add_argument('--width',
                        dest    = 'width',
                        metavar = 'WIDTH',
                        default = plt.rcParams.get('figure.figsize')[0],
                        help    = 'Width of plot in inches.')
    parser.add_argument('--height',
                        dest    = 'height',
                        metavar = 'HEIGHT',
                        default = plt.rcParams.get('figure.figsize')[1],
                        help    = 'Height of plot in inches.')
    parser.add_argument('--dpi',
                        dest    = 'dpi',
                        metavar = 'DPI',
                        default = plt.rcParams.get('figure.dpi'),
                        help    = 'DPI for plotting.')
    parser.add_argument('--image-format',
                        dest    = 'image_format',
                        metavar = 'FORMAT',
                        default = 'png',
                        help    = 'Image format.')
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

    if 'epoch' in data_frame.columns:
        tz = timezone.utc if args.utc else system_timezone_info()
        t = [datetime.fromtimestamp(epoch, tz) for epoch in data_frame['epoch']]
    else:
        # TODO: treat 'time' column as the timestamp if 'epoch' column does not exist.
        t = np.arange(0, len(data_frame))

    for column_name in data_frame.columns:
        if column_name == 'system time' or column_name == 'epoch':
            continue

        fig = plot(t, data_frame, column_name, tz, args)
        
        output_filename = '.'.join((to_filename_base(column_name), args.image_format))
        output_path = output_dir / output_filename
        output_dir.mkdir(parents = True, exist_ok = True)
        fig.savefig(output_path)
        print(f'Generated a plot as {output_path}')

        if not args.show_plot:
            plt.close(fig)

    if args.show_plot:
        plt.show()
    
if __name__ == "__main__":
    main()
