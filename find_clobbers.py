# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 13:09:28 2011
Input: c- source function containing code and interface
Output: list of expected clobber list parameters
@author: lkonis
"""
import sys
import re
import tkFileDialog
from Tkinter import *


def find_clobbers_in_file(filename):
    iam_in_interface = 0
    list_of_interface = []
    list_of_clobbers = []
    in_assembly = 0
    # full possible:  extern "C" assembly void _A0_ dcremoval2m_wrap(

    interface_pattern = """
    ^                   # beginning of string
    (.*)                # space or 'extern "C"' and so on
    assembly            # restricted word
    \s+                 # space
    (\w+)               # return type (void, int, fix etc.)
    \s+                 # space
    (_[ABXY][0-3]_|_I[0-9]_|_I1[0-5]_|_NM[0-9]_|_NM1[0-5]_|nm[0-9]_t|nm1[0-5]_t)*\s* # output macro + space
    (\w*)               # function name, not including after left parentesis
    \s*\(*(.*)$         # possibly opening parenthesis with possible list
    """
    #    \s*                 # space
    #    \((.*)$             # opening parentesis and possibly list with interface definition

    reg_pattern = '([abxy][0-3]|i[0-9]|i1[0-5]|nm[0-9]|nm1[0-5])'

    try:
        fi = open(filename, 'rb')
    except:
        print("can't open file " + filename)
        return
    line = 1
    missing_clobbers_results = []
    while (line):
        # read next line
        line = fi.readline()

        # single comment line
        if re.search('^\s*//', line):
            continue
        if re.search('^\s*#', line):
            continue
        if re.search('^\s*$', line):
            continue
        # remove two types of single-line comments in active line
        line = re.sub('\/\*.*\*\/', '', line)
        line = re.sub('//.*', '', line)

        # identify inner interface line
        if iam_in_interface == 1:
            s = re.search('(.*)\)*', line)  # that is, and end
            line = s.group()
            interface_vars = re.findall(reg_pattern + '_', line, re.IGNORECASE)
            list_of_interface.extend(interface_vars)
            s = re.search('clobbers\s*\((.*?)\)', line)
            if s:
                list_of_clobbers = re.sub(' ', '', s.groups()[0]).split(',')
            if re.search('\)', line):
                iam_in_interface = 0
            continue

        # identify begining of interface line
        s = re.search(interface_pattern, line, re.VERBOSE)
        if s is not None:
            in_assembly = 1
            if 'inline' in s.groups()[0]:
                in_assembly = 0
                continue
            else:
                all_terms = s.groups()[1:]
            return_type = all_terms[0]

            if re.search('inline', line):
                return_type = 'inline_' + return_type
            if all_terms[1]:
                out_var = re.sub('[_\s]', '', all_terms[1])
                list_of_interface = [out_var]
            function_name = all_terms[2]
            if len(all_terms) < 4:  # not re.search('\)',all_terms[3]):
                iam_in_interface = 1
            else:
                interface_vars = re.findall(reg_pattern + '_', all_terms[3], re.IGNORECASE)
                list_of_interface.extend(interface_vars)
                if not re.search('\)', line):
                    iam_in_interface = 1
                # check also for clobbers list
                s = re.search('clobbers\s*\((.*?)\)', line, re.VERBOSE)
                if s:
                    list_of_clobbers = re.sub(' ', '', s.groups()[0]).split(',')
            continue
        if iam_in_interface == 1:
            s = re.search('\)', line)  # that is, and end
            if s:
                iam_in_interface = 0

        # single line of clobbers list
        if in_assembly:
            s = re.search('clobbers\s*\((.*?)\)', line)
            if s:
                list_of_clobbers = re.sub(' ', '', s.groups()[0])
                list_of_clobbers = list_of_clobbers.split(',')
            if "asm_begin" in line:
                list_of_body = find_body_regs(fi)
                list_of_body = sorted(set(list_of_body))
                list_of_body = [x.lower() for x in list_of_body]
                list_of_interface = [x.lower() for x in list_of_interface]
                # calculate correct clobbers list
                list_of_correct_clobbers = sorted(set(list_of_body) - set(list_of_interface))
                in_assembly = 0

                try:
                    list_of_missing_clobbers = calc_missing_clobbers(return_type, function_name, list_of_body,
                                                                     list_of_interface, list_of_clobbers,
                                                                     list_of_correct_clobbers)
                    missing_clobbers_results.append((return_type, function_name, list_of_missing_clobbers))

                except:
                    # print 'can\'t determine for this function'
                    return [0, filename]
                # clear lists
                list_of_body = []
                list_of_interface = []
                list_of_clobbers = []

    fi.close()
    return missing_clobbers_results


def calc_missing_clobbers(return_type, function_name, list_of_body, list_of_interface, list_of_clobbers,
                          list_of_correct_clobbers):
    list_of_missing_clobbers = sorted(set(list_of_correct_clobbers) - set(list_of_clobbers))
    list_of_extra_clobbers = sorted(set(list_of_clobbers) - set(list_of_correct_clobbers))
    shell_print = 0
    if shell_print:
        print '\nFunction:\n============\n' + str(return_type) + ' ' + str(function_name)
        print '\nBody registers:\n=====================\n' + str(list_of_body)
        print '\nInterface registers:\n=====================\n' + str(list_of_interface)
        print '\nRegisters declared in clobber list:\n=====================\n' + str(list_of_clobbers)
        print '\nCorrect clobber list:\n=====================\n' + str(list(list_of_correct_clobbers))
        print '\nMissing clobbers: ' + str(list(list_of_missing_clobbers)) + '\nRedundant clobbers:' + str(
            list(list_of_extra_clobbers))

    return list_of_missing_clobbers


# find registers that appear inside code-body
def find_body_regs(fi):
    list_of_body = []
    iam_in_comment = 0

    # define all registers pattern
    reg_pattern = '[^\\w]([abxy][0-3]|i[0-9]|i1[0-5]|nm[0-9]|nm1[0-5])'  # '([abxy][0-3]|i[0-7]|nm[0-7])'
    line = 1
    while (line):
        line = fi.readline()

        # identify end of multi-line comments
        if (iam_in_comment == 1):
            if (re.search('\*\/', line) is not None):
                iam_in_comment = 0
                line = re.sub('.*\*\/', '', line)
            else:
                continue

        # comment has the form: /* ..code... */
        line = re.sub('\/\*.*\*\/', '', line)  # remove single-line comments in active line

        # remove single-line comments
        # 1. lines that are comment starts with //
        if re.search('^\s*//', line):
            continue
        # 2. comment after code (starts with // )
        line = re.sub('//.*', '', line)

        # identify multi-line comments
        if (iam_in_comment == 0) & (re.search('.*\/\*.*$', line) is not None):
            iam_in_comment = 1
            line = re.sub('\/\*.*$', '', line)

        if "asm_end" in line:
            return list_of_body
        # can't remember why I put [^0] but it's wrong
        #        addthis = re.findall('[^0]'+reg_pattern, line, re.IGNORECASE)
        addthis = re.findall(reg_pattern, line, re.IGNORECASE)
        list_of_body.extend(addthis)


"""
" main function that 
" if input=None, asks for single file and print results
" if input=some file name then function returns tuple that contains missing clobbers etc.
"
"""


def main_clobbers(filename):
    if filename == None:
        use_gui = 1
    else:
        use_gui = 2

    contLoop = 1

    # TODO: The endless loop is not really needed here
    while contLoop == 1:
        if not use_gui:
            contLoop = 0
        if use_gui == 1:  # open file dialog for single file search
            # the next two lines are just to close anoying 'root' window
            root = Tk()
            root.withdraw()
            filename = tkFileDialog.askopenfilename(parent=root, filetypes=[("All files", "*"), ("Header files", "*.h"),
                                                                            ("c files", "*.c")],
                                                    initialdir='C:\TFS\Dooku\Main\DSP\signalprocessing\mod')
        elif use_gui == 0:
            args = sys.argv[1:]
            if not args:
                print 'usage: find_clobbers.py file [file ...]'
                sys.exit(1)
            else:
                filename = args[0]
        elif use_gui == 2:
            filename = filename
        else:
            print "error"
            sys.exit(1)
        if filename == '':
            print 'no filename chose'
            contLoop = 0
            sys.exit(1)

        missing_clobbers_results = find_clobbers_in_file(filename)
        if (len(missing_clobbers_results) > 0):
            if (missing_clobbers_results[0] != 0):
                # only for local version
                if (use_gui == 1):
                    print 'missing clobbers:\n'
                    for tup in missing_clobbers_results:
                        try:
                            if tup[0] == 0:
                                print tup[1] + ': can\'t decide for this function'
                            if len(tup[2]):
                                print 'in file: ' + filename
                                print_result((filename, tup))
                        except:
                            print 'wwoops'
                # For search folder version - return file name  + all lists
                else:
                    return (filename, missing_clobbers_results)
        return


# this print function is used in single-file clobbers-find version
def print_result(in_tup):
    filename = in_tup[0]
    in_tup = in_tup[1]
    print 'Function ' + in_tup[0] + ' ' + in_tup[1] + '\n\tmissing clobbers: ' + str(in_tup[2]) + '\n\n'

    frame = Tk()
    w = Label(frame, text='In File %s\n\nFunction %s %s has missing clobbers:\n%s' % (
    filename, in_tup[0], in_tup[1], str(in_tup[2])), font=("Helvetica", 12), justify=LEFT)
    w.pack()
    w.mainloop()


if __name__ == '__main__':
    """
    local run version
    the argument is None and therefore a local file dialog will be executed
    """
    main_clobbers(None)
