import argparse
import sys
import io
import copy
import yaml
import errno

import cl_bindgen.processfile as processfile
from cl_bindgen.processfile import ProcessOptions

class BatchException(Exception):

    def __init__(self, error_string):
        Exception.__init__(self, error_string)

def _add_dict_to_option(option, dictionary):
    option = copy.copy(option)

    output = dictionary.get('output')
    args = dictionary.get('arguments')
    package = dictionary.get('package')
    if output:
        option.output = output
    if args:
        options.arguments.extend(args)
    if package:
        option.package = package

    return option


def _add_args_to_option(option, args):
    """ Return a new option object with the options specified by `args` and based on 'option' """
    option = copy.copy(option)
    if hasattr(args, 'output') and args.output:
        option.output = args.output
    if args.arguments:
        option.arguments.extend(args.arguments)
    if hasattr(args, 'package') and args.package:
        option.package = args.package
    if args.force:
        option.force = True
    return option

def _verify_document(document):
    return 'files' in document and 'output' in document

def process_batch_file(batchfile, options):
    """ Perform the actions specified in the batch file with the given base options

    If options are specified in the batch file that override the options given, those
    options will be used instead.
    """
    with open(batchfile, 'r') as f:
        data = yaml.load_all(f, Loader=yaml.Loader)
        for document in data:
            if not _verify_document(document):
                raise BatchException(f'Missing fields in batchfile "{batchfile}"')
            options = _add_dict_to_option(options, document)
            processfile.process_files(document['files'], options)

def _arg_batch_files(arguments, options):
    """ Perform the actions described in batch_files using `options` as the defaults """

    options = _add_args_to_option(options, arguments)
    try:
        for batch_file in arguments.inputs:
            process_batch_file(batch_file, options)
    except BatchException as err:
        print(f'Error: {str(err)}.\nExiting')
        exit(errno.EINVAL)
    except processfile.ParserException as err:
        print(f'Error encountered while processing file:')
        print(err.format_errors(), file=sys.stderr)
        print('\nNo output produced', file=sys.stderr)
        exit(1)

def _arg_process_files(arguments, options):
    """ Process the files using the given parsed arguments and options """

    options = _add_args_to_option(options, arguments)
    try:
        processfile.process_files(arguments.inputs, options)
    except FileNotFoundError as err:
        print(f'Error: Input file "{err.strerror}" not found.\nNo output produced.',
              file=sys.stderr)
        exit(err.errno)
    except IsADirectoryError as err:
        print(f'Error: "{err.strerror}" is a directory.\nNo output produced.',
              file=sys.stderr)
        exit(err.errno)
    except processfile.ParserException as err:
        print(f'Error encountered while processing file:')
        print(err.format_errors(), file=sys.stderr)
        print('\nNo output produced', file=sys.stderr)
        exit(1)

def _build_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--version',action='version',
                        version='CL-BINDGEN 1.0.3',
                        help="Print the version information")
    subparsers = parser.add_subparsers()

    batch_parser = subparsers.add_parser('batch', aliases=['b'],
                                         help="Process files using specification files",
                                         description="Instead of specifying options on the command line, .yaml files can be used to specify options and input files")
    batch_parser.add_argument('inputs', nargs='+',
                              metavar='batch files',
                              help="The batch files to process")
    batch_parser.add_argument('-a', metavar='compiler arguments',
                                dest='arguments',
                                nargs=argparse.REMAINDER,
                                help='Consume the rest of the arguments and pass them to libclang')
    batch_parser.add_argument('-f',
                              action='store_true',
                              dest='force',
                              help='ignore parsing errors')
    batch_parser.set_defaults(func=_arg_batch_files)


    process_parser = subparsers.add_parser('files',aliases=['f'],
                                           help="Specify options and files on the command line")
    process_parser.add_argument('inputs',nargs='+',
                                metavar="input files",
                                help="The input files to cl-bindgen")
    process_parser.add_argument('-o',
                                metavar='output',
                                dest='output',
                                help="Specify where to place the generated output.")
    process_parser.add_argument('-p',
                                metavar='package',
                                dest='package',
                                help="Output an in-package form with the given package at the top of the output")
    process_parser.add_argument('-a', metavar='compiler arguments',
                                dest='arguments',
                                nargs=argparse.REMAINDER,
                                help='Consume the rest of the arguments and pass them to libclang')
    process_parser.add_argument('-f',
                                action='store_true',
                                dest='force',
                                help='ignore parsing errors')
    process_parser.set_defaults(func=_arg_process_files)

    return parser

def dispatch_from_arguments(arguments, options):
    """ Use the given arguments and manglers to perform the main task of cl-bindgen """

    parser = _build_parser()

    if not len(arguments) > 0:
        parser.print_help()
        exit(1)

    args = parser.parse_args(arguments)

    return args.func(args, options)
