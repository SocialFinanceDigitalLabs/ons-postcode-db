from sfdata_postcodes import spec
from sfdata_postcodes.data import extras
from sfdata_postcodes.data.codes import CodeContainer
from sfdata_postcodes.data.postcode import PostcodeRow
from sfdata_postcodes.zipfile import read_csv, read_csv_with_progress


def read_reference_file(zipfile, filename, extras=None) -> CodeContainer:
    container = CodeContainer()
    for row in read_csv(zipfile, filename):
        container.add(row[0], row[1])

    if extras:
        for extra in extras:
            container.add(extra[0], extra[1])
    return container


def read_all(zipfile):
    return {
        "country": CodeContainer(initial_values=extras.COUNTRIES),
        "county": read_reference_file(zipfile, spec.COUNTY_FILE),
        "electoral_division": read_reference_file(zipfile, spec.ELECTORAL_DIVISION, extras=extras.ELECTORAL_DIVISIONS),
        "local_authority_district": read_reference_file(zipfile, spec.LOCAL_AUTHORITY_DISTRICTS),
        "urban_rural_classification": read_reference_file(zipfile, spec.RURAL_URBAN),
    }


def read_postcodes(zipfile, max_postcodes=None, progress=True):
    if progress:
        postcodes = read_csv_with_progress(zipfile, spec.POSTCODE_FILE)
    else:
        postcodes = read_csv(zipfile, spec.POSTCODE_FILE)

    for ix, row in enumerate(postcodes):
        if max_postcodes and ix >= max_postcodes:
            break

        yield PostcodeRow.from_row(row)

