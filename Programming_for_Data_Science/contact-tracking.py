from argparse import ArgumentParser
from collections import Counter
from collections import defaultdict
from datetime import timedelta

import pandas as pd
import numpy as np
from matplotlib import pyplot as plt


def number_of_people(df):
    return len(set(df['phone1'].unique()).union(df['phone2'].unique()))


def contact_stats(df):
    df[['contact']] = df[['phone1', 'phone2']].apply(tuple, axis=1)
    df = df[['when', 'contact']]
    df = df.groupby(pd.Grouper(key='when', freq='1D')).count()
    minimum = df['contact'].min()
    maximum = df['contact'].max()
    mean = df['contact'].mean()
    return minimum, maximum, mean


def find_infections(df, first_infected, incubation, recovery):
    infections = defaultdict(dict)
    first_day = df['when'].min().date()
    infections[first_infected] = {
        'infected': first_day - timedelta(days=1),
        'start': first_day + timedelta(days=incubation),
        'end': first_day + timedelta(days=recovery),
    }
    df = df[
        df['when'] >= pd.Timestamp(
            infections[first_infected]['start'],
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            nanosecond=0
        )
    ]
    for row in df.itertuples():
        if row.phone1 in infections and row.phone2 not in infections:
            infected = infections[row.phone1]
            # me < einai opws ta paradeigmata ta apotelesmata, enw me <= einai to swsto
            if row.when >= infected['start'] and row.when < infected['end']: 
                infections[row.phone2] = {
                    'infected': row.when.date(),
                    'start': row.when.date() + timedelta(days=incubation),
                    'end': row.when.date() + timedelta(days=recovery),
                }
        elif row.phone2 in infections and row.phone1 not in infections:
            infected = infections[row.phone2]
            # me < einai opws ta paradeigmata ta apotelesmata, enw me <= einai to swsto
            if row.when >= infected['start'] and row.when < infected['end']: 
                infections[row.phone1] = {
                    'infected': row.when.date(),
                    'start': row.when.date() + timedelta(days=incubation),
                    'end': row.when.date() + timedelta(days=recovery),
                }
    return infections


def count_infections(infections):
    counter = Counter()
    for _, v in infections.items():
        counter[v['infected']] += 1
    return counter


def plot_infections(df, infections_counter):
    first_day = df['when'].min().date() - timedelta(days=1)
    last_day = df['when'].max().date()
    current = first_day
    new_df_dict = {'when': [], 'cases': []}
    while current <= last_day:
        new_df_dict['when'].append(current)
        new_df_dict['cases'].append(infections_counter[current])
        current += timedelta(days=1)
    when = new_df_dict.pop('when')
    new_df = pd.DataFrame(new_df_dict, index=when)
    cum_df = new_df.cumsum()
    # whole_df = pd.concat([new_df, cum_df], axis=1)
    _, axes = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(30, 20))
    new_df[new_df.index > first_day].plot.bar(ax=axes[0], color='blue', legend=False)
    cum_df[cum_df.index > first_day].plot.bar(ax=axes[1], color='red', legend=False)
    plt.savefig('diagrams.png', bbox_inches='tight')


def main(filename, phone, incubation, recovery):
    df = pd.read_csv(filename, header=0)
    df.columns = [c.lower() for c in df.columns]
    df['when'] = pd.to_datetime(df['when'])
    df = df.sort_values(by=['when'])
    # print(df)
    people = number_of_people(df)
    print(f'people = {people}')
    minimum, maximum, mean = contact_stats(df)
    print(f'max contacts per day = {maximum}')
    print(f'min contacts per day = {minimum}')
    print(f'average contacts per day = {mean:.3f}')
    infections = find_infections(df, phone, incubation, recovery)
    print(f'total infected = {len(infections)}')
    infections_counter = count_infections(infections)
    print(f'max cases per day = {infections_counter.most_common(1)[0][1]}')
    plot_infections(df, infections_counter)


if __name__ == '__main__':
    parser = ArgumentParser(prog='tracking')
    parser.add_argument('filename', help='The csv file.')
    parser.add_argument('phone', type=int, help='Phone number of first victim.')
    parser.add_argument('incubation', type=int, help='Time for the virus to incubate (in days).')
    parser.add_argument('recovery', type=int, help='Time for the virus to subside (in days).')
    args = parser.parse_args()
    main(args.filename, args.phone, args.incubation, args.recovery)
