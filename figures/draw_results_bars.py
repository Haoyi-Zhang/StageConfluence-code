"""Draw exact finite-family property counts as a vector bar chart."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager, pyplot as plt
from plot_font import PDF_METADATA, regular_libertine

HERE = Path(__file__).resolve().parent
METRICS = [('direct_confluent', 'state-confluent'), ('modular_true', 'modular criterion'),
           ('unique_terminal_program', 'unique program ID'), ('guard_persistent', 'guard persistent'),
           ('saturated_peaks_join', 'saturated peaks join')]
BOX = (-5.173579078455791, -13.436931506849316, 346.9566525529266, 105.36458281444582)


def refresh_data(summary, target):
    totals = json.loads(summary.read_text(encoding='utf-8'))['totals']
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['metric', 'label', 'count', 'instances'])
        writer.writerows((key, label, totals[key], totals['instances']) for key, label in METRICS)


def draw(data, output, font):
    with data.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if [(r['metric'], r['label']) for r in rows] != METRICS:
        raise ValueError('The original five properties and category order are required.')
    if [int(r['count']) for r in rows] != [207069, 134977, 235741, 305036, 349208] or any(int(r['instances']) != 451736 for r in rows):
        raise ValueError('The retained finite-family counts changed.')
    size = 8*72/72.27
    prop = font_manager.FontProperties(fname=str(font), size=size)
    xmin, ymin, xmax, ymax = BOX
    xunit, yunit = 2*.115*72/25.4, 7*72/25.4
    with plt.rc_context({'font.family': prop.get_name(), 'font.size': size, 'pdf.fonttype': 42, 'text.usetex': False}):
        fig = plt.figure(figsize=((xmax-xmin)/72, (ymax-ymin)/72))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set(xlim=(xmin/xunit, xmax/xunit), ylim=(ymin/yunit, ymax/yunit))
        ax.set_axis_off()
        centers = [i+.775 for i in range(5)]
        ax.barh(centers, [int(r['count'])/1000 for r in rows], height=.55,
                color='white', edgecolor='black', linewidth=.4*72/72.27)
        for y, row in zip(centers, rows):
            ax.text(int(row['count'])/1000+4+(size/3)/xunit, y,
                    f"{row['label']}: {int(row['count']):,}", ha='left', va='center', fontproperties=prop)
        for end in ((415, 0), (0, 5.3)):
            ax.annotate('', xy=end, xytext=(0, 0),
                        arrowprops={'arrowstyle': '->', 'linewidth': .4*72/72.27, 'shrinkA': 0, 'shrinkB': 0})
        ax.text(415+(size/3)/xunit, 0, 'thousands of systems', ha='left', va='center', fontproperties=prop)
        for value in (0, 100, 200, 300, 400):
            ax.vlines(value, 0, -.08, color='black', linewidth=.4*72/72.27)
            ax.text(value, -.08-(size/3)/yunit, str(value), ha='center', va='top', fontproperties=prop)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, metadata=PDF_METADATA)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path)
    parser.add_argument('--data', type=Path, default=HERE/'results-bars.csv')
    parser.add_argument('--out', type=Path, default=HERE/'results-bars.pdf')
    parser.add_argument('--refresh-data', type=Path, metavar='SUMMARY', help='Read saved staged-enumeration totals; do not rerun enumeration.')
    args = parser.parse_args()
    if args.refresh_data:
        refresh_data(args.refresh_data, args.data)
    draw(args.data, args.out, regular_libertine(HERE, args.font))
    print(args.out.name)


if __name__ == '__main__':
    main()
