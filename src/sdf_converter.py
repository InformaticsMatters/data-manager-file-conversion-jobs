#!/usr/bin/env python
"""Convert from SDF file to file with a selected mime-type
"""
import argparse
import json
import re
import uuid
import datetime
import logging
import os
import gzip
from typing import Any, Dict, List, Optional


_MIME_TYPE_MAP = {
    'chemical/x-mdl-sdfile': 'sdf',
    'application/x-squonk-dataset-molecule-v2+json': 'json',
    'application/schema+json': 'json_schema',
}

# Two loggers - one for basic logging, one for events.
basic_logger = logging.getLogger('basic')
basic_logger.setLevel(logging.INFO)
basic_handler = logging.StreamHandler()
basic_formatter = logging.Formatter('%(asctime)s # %(levelname)s %(message)s')
basic_handler.setFormatter(basic_formatter)
basic_logger.addHandler(basic_handler)

event_logger = logging.getLogger('event')
event_logger.setLevel(logging.INFO)
event_handler = logging.StreamHandler()
event_formatter = logging.Formatter('%(asctime)s # %(levelname)s -EVENT- %(message)s')
event_handler.setFormatter(event_formatter)
event_logger.addHandler(event_handler)

# Get and display the environment material
# (guaranteed to be provided)
# using the basic (non-event) logger
dataset_filename = os.getenv('DT_DATASET_FILENAME')
dataset_input_path = os.getenv('DT_DATASET_INPUT_PATH')
dataset_output_path = os.getenv('DT_DATASET_OUTPUT_PATH')
dataset_output_format = os.getenv('DT_DATASET_OUTPUT_FORMAT')
dataset_output_filename = os.getenv('DT_DATASET_OUTPUT_FILENAME')


def is_number(value: str) -> int:
    """Determines the number type for the property value
    :return 0 for text, 1 for float, 2 for integer
    """
    try:
        float_number = float(value)
    except ValueError:
        return 0
    else:
        if float_number.is_integer():
            return 2
        return 1


def add_sdf_property(properties: Dict[str, str], propname: str, propvalue: List[str]):
    """Adds a property (name, value) pair to the properties dictionary"""

    if propvalue[len(propvalue) - 1]:
        # property block should end with an empty line, but some SDFs are buggy
        properties[propname] = '\n'.join(propvalue)
    else:
        properties[propname] = '\n'.join(propvalue[:-1])


def check_name_in_properties(properties, prop_types):
    """Check the name in the properties and set type."""

    for name in properties:
        if name not in prop_types:
            prop_types[name] = 2
        prop_name_type = is_number(properties[name])
        if prop_name_type < prop_types[name]:
            prop_types[name] = prop_name_type

    return prop_types


class ConvertFile:
    """Class ConvertFile.

    Converts from an input mime-type to an output mime-type.
    """

    errors: int = 0
    lines: int = 0
    records: int = 0

    def convert(self, to_mime_type: str, infile: str, outfile: str) -> bool:
        """Dispatch method"""
        to_type: Optional[str] = _MIME_TYPE_MAP.get(to_mime_type)
        assert to_type

        method_name = 'convert_sdf_to_' + str(to_type)
        # Get the method from 'self'. Default to a lambda.
        method = getattr(self, method_name, lambda: "Invalid conversion")
        # Call the method as we return it
        return method(infile, outfile)  # type: ignore

    def process_molecules_json(self, file, outfile):
        """Process molecules in SDF file"""

        pattern: str = '^>  <(.*)>'
        molecule = {}
        molblock = []
        properties: Dict[str, str] = {}

        # Loop through molecules
        while True:
            self.lines += 1

            # Get next line from file
            line = file.readline()

            # if line is empty
            # end of file is reached
            if not line:
                break

            # remove newline chars
            text = line.rstrip('\n\r')
            molblock.append(text)

            # 'M  END' signifies the end of the molblock. The properties will follow
            if text == 'M  END':
                propname = None
                propvalue = []
                if molblock[0]:
                    molecule['name'] = molblock[0]
                molblock = '\n'.join(molblock)
                molecule['molblock'] = molblock

                # Loop through properties
                while True:
                    self.lines += 1
                    line = file.readline()

                    # if line is empty
                    # end of file is reached
                    if not line:
                        break

                    text = line.strip()

                    # '$$$$' signifies the end of the record
                    if text == '$$$$':
                        self.records += 1
                        if propname:
                            add_sdf_property(properties, propname, propvalue)

                        record = {
                            'uuid': str(uuid.uuid4()),
                            'molecule': molecule,
                            'values': properties,
                        }
                        json_str = json.dumps(record)
                        if self.records > 1:
                            outfile.write(',')
                        outfile.write(json_str)

                        molecule = {}
                        molblock = []
                        properties: Dict[str, str] = {}
                        break

                    result = re.match(pattern, text)
                    if result:
                        if propname:
                            add_sdf_property(properties, propname, propvalue)
                        propname = result.group(1)
                        propvalue = []
                    else:
                        propvalue.append(text)

        outfile.write(']')

    def convert_sdf_to_json(self, infile, outfile) -> bool:
        """Converts the given SDF file into a Squonk json file.
        Returns True if file successfully converted.
        """
        if infile.endswith('.gz'):
            file = gzip.open(infile, 'rt')
        else:
            file = open(infile, 'rt', encoding='utf-8')
        outfile = open(outfile, 'w', encoding='utf-8')
        outfile.write('[')

        try:
            self.process_molecules_json(file, outfile)
        finally:
            outfile.close()

        if self.errors > 0:
            return False
        return True

    def process_properties_json(self, file):
        """Process properties in SDF file"""

        pattern = '^>  <(.*)>'
        properties = {}
        prop_types = {}
        # Loop through molecules
        while True:
            self.lines += 1
            # Get next line from file
            line = file.readline()

            # if line is empty
            # end of file is reached
            if not line:
                break
            # remove newline chars
            text = line.rstrip('\n\r')

            # 'M  END' signifies the end of the molblock. The properties will follow
            if text == 'M  END':
                propname = None
                prop_value = []

                # Loop through properties
                while True:
                    self.lines += 1
                    line = file.readline()

                    # if line is empty
                    # end of file is reached
                    if not line:
                        break
                    text = line.strip()

                    # '$$$$' signifies the end of the record
                    if text == '$$$$':
                        self.records += 1
                        if propname:
                            add_sdf_property(properties, propname, prop_value)
                        prop_types = check_name_in_properties(properties, prop_types)

                        properties = {}
                        break

                    result = re.match(pattern, text)
                    if result:
                        if propname:
                            add_sdf_property(properties, propname, prop_value)
                        propname = result.group(1)
                        prop_value = []
                    else:
                        prop_value.append(text)

        return prop_types

    def convert_sdf_to_json_schema(self, infile, outfile) -> bool:
        """Converts the given SDF file into a Squonk json schema.
        Returns True if file successfully converted.
        """

        # sdf properties for internal json format.
        # Used in the json schema on internal conversion.
        _json_properties_sdf = {
            'uuid': {'type': 'string', 'description': 'Unique UUID'},
            'molecule': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'Molecule name'},
                    'molblock': {
                        'type': 'string',
                        'description': 'Molfile format 2D or 3D representation',
                    },
                    'isosmiles': {
                        'type': 'string',
                        'description': 'Isomeric SMILES representation',
                    },
                    'stdsmiles': {
                        'type': 'string',
                        'description': 'Standardised non-isomeric SMILES representation',
                    },
                },
            },
        }
        _lookups = {0: 'string', 1: 'number', 2: 'integer'}

        # Extract the properties from the file
        if infile.endswith('.gz'):
            file = gzip.open(infile, 'rt')
        else:
            file = open(infile, 'rt', encoding='utf-8')

        try:
            prop_types = self.process_properties_json(file)
        finally:
            file.close()

        # Add the properties from the file to the schema
        values: Dict[str, Any] = {}
        _json_properties_sdf['values'] = {'type': 'object', 'properties': values}
        for prop_name, prop_type in prop_types.items():
            values[prop_name] = {'type': _lookups[prop_type]}

        schema_sdf = {
            '$schema': 'http://json-schema.org/draft/2019-09/schema#',
            'description': 'Automatically created from '
            + infile
            + ' on '
            + str(datetime.datetime.now()),
            'properties': _json_properties_sdf,
        }

        json_str: str = json.dumps(schema_sdf)
        with open(outfile, 'w', encoding='utf-8') as schema_file:
            schema_file.write(json_str)

        if self.errors > 0:
            return False
        return True


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='SDF File Converter')
    parser.add_argument('-i', '--input', help='Input file (SDF)')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-m', '--mime-type', help='Output MIME type')
    args = parser.parse_args()

    # format input file path and output file path.
    basic_logger.info('SDF Converter')
    event_logger.info('Processing %s...', args.input)

    converter = ConvertFile()
    processed: bool = converter.convert(args.mime_type, args.input, args.output)

    if processed:
        basic_logger.info('SDF Converter finished successfully')
    else:
        basic_logger.info('SDF Converter failed')

    basic_logger.info('lines processes=%s', converter.lines)
    basic_logger.info('errors=%s', converter.errors)
