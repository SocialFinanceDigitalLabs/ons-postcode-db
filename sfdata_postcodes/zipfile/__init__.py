import csv
from io import TextIOWrapper

from tqdm import tqdm


def read_csv(zipfile, filename, skip_rows=1):
    with zipfile.open(filename, 'r') as file:
        csv_reader = csv.reader(TextIOWrapper(file))
        for _ in range(skip_rows):
            next(csv_reader)  # skip header
        yield from csv_reader


def read_csv_with_progress(zipfile, filename, skip_rows=1):
    zip_info = zipfile.getinfo(filename)
    last_pos = 0

    with zipfile.open(filename, 'r') as file:
        with tqdm(total=zip_info.file_size) as progress:
            csv_reader = csv.reader(TextIOWrapper(file))
            for _ in range(skip_rows):
                next(csv_reader)  # skip header

            for row in csv_reader:
                progress.update(file.tell() - last_pos)
                last_pos = file.tell()
                yield row

