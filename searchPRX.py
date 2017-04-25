# -*- coding: utf-8 -*-
"""
Created on Mon Oct 19 15:50:01 2015
Input: prx - file containing hierarchical list of c, h, source code and interface
Output: list with full paths to all source files
@author: lkonis
"""
import os
import re
import tkFileDialog
import Tkinter

import sys


class PRX:

    # globals



    def __init__(self):
        self.c_source = ['']
        self.app_folder = ''
        self.prj_file = ''

    # create list of source files out of project (prx) file exists in application folder
    # if argument is None, use a gui dialog
    def list_prx(self, appsFolder):
    # find path to (application) project folder
        if appsFolder is None:
            use_gui = 1
        else:
            use_gui = 2

        # open file dialog for single file search
        if use_gui == 1:  # the next two lines are just to close anoying 'root' window
            root = Tkinter.Tk()
            root.withdraw()
            basefolder = r'C:\git\DookuMain\hi-platform\algo\firmware\app'
            if not os.path.isdir(basefolder):
                sys.exit(1)
            try:
                self.app_folder = tkFileDialog.askdirectory(parent=root, initialdir=basefolder)
                #/Dooku1_tmp/hi-platform/algo/firmware/app')
                # filetypes=[ ("All files", "*"), ("Project files", "*.prx")],
            except:
                os.error('initial dir doesnt exist')
            if self.app_folder.endswith('app'):
                self.app_folder = os.path.join(self.app_folder, 'App_Audio')
        elif use_gui == 2:
            self.app_folder = appsFolder

    # find base firmware path
        if 'firmware' in self.app_folder:
            fw_path = self.app_folder.split('firmware')
            fw_path = os.path.join(fw_path[0], 'firmware')
            print fw_path[:]
        else:
            print 'no folder chosen'
            sys.exit(1)

    # scan app folder
        for cfile in os.listdir(self.app_folder):
            if cfile.endswith('prx'):
                self.prj_file = os.path.join(self.app_folder, cfile)
            if cfile.endswith('c'):
                self.c_source.append(os.path.join(self.app_folder, cfile))

    # look for project file (*.prx)
    def find_sources(self, fn):
        with open(fn, 'r') as f:
            fc = f.read()  # file content
            s = re.findall(r'name="(.*)" path="(.*)"', fc)

        sf_list = []

        for sf in s:
            # joined path
            jp = os.path.join(self.app_folder, sf[1], sf[0])
            if os.path.isfile(jp):
                sf_list.append(jp)
            else:
                sys.exit(1)
        return sf_list

    def extract_valid_lines(self, fc):
        f_txt = fc.readlines()
        # remove all comments, i.e. // /*
        meaningfull_line = ['']
        in_comment = False
        for line in f_txt:
            if in_comment == True:
                if '*/' in line:
                    in_comment = False
                    line = line.split('*/')[1]
                    if re.match(r'^\s*$', line):
                        continue
                else:
                    continue
            # remove single line comments
            line = line.split('//')[0]
            # detect multi line comments
            if '/*' in line:
                if '*/' in line:
                    continue
                else:
                    line = line.split('/*')[0]
                    in_comment = True

            if re.match(r'^\s*$', line):
                continue
            meaningfull_line.append(line)
        return meaningfull_line

    # extract global symbols from a source file
    def collect_glob_from_file(self, fc):
        out = ['']
        is_in_func_dec = False
        is_in_func_def = False
        pend_func_def = False
        curl_stack = 0
        is_assembly = False
        is_void = False
        functions = ['']
        lines = self.extract_valid_lines(fc)
        for line in lines:
            if '{' in line:
                curl_stack += 1
                if '}' in line:
                    curl_stack = max(curl_stack - 1, 0)
                    if is_in_func_def and curl_stack == 0:
                        is_in_func_def = False
                    continue
            if '}' in line:
                curl_stack = max(curl_stack - 1,0)
            if is_in_func_def and curl_stack == 0:
                is_in_func_def = False

            if pend_func_def:
                if '{' in line:
                    is_in_func_def = True
                    pend_func_def = False
                else:
                    print 'ERROR'
                    continue

            # if is_in_func_def:
            #     if curl_stack==1 and '}' in line:
            #         is_in_func_def = False
            #     else:
            #         continue

            if is_in_func_dec:
                if ')' in line:
                    is_in_func_dec = False
                    pend_func_def = True


            # detect start of function definition
            if curl_stack == 0 and is_in_func_dec == False and '(' in line:
                if ')' not in line:
                    is_in_func_dec = True
                else:
                    if '{' in line:
                        is_in_func_def = True
                    else:
                        pend_func_def = True
                this_line = line.split('(')[0].split()
                function_name = this_line[-1]
                if 'assembly' in this_line:
                    is_assembly = True
                    this_line.remove('assembly')
                if 'void' in this_line:
                    is_void = True
                    this_line.remove('void')
                    function_type = 'void'
                functions.append((function_type, function_name))
            last_line = line
        return functions





    # loop over all files and make a list of global symbols
    def collect_globals(self, source_list):
        global_variables = []

        for sf in source_list:
            with file(sf) as f:
                gv = self.collect_glob_from_file(f)
                global_variables.append(gv)
        return global_variables


if __name__ == '__main__':
    p = PRX()
    p.list_prx(None)
    source_list = p.find_sources(p.prj_file)
    global_variables = p.collect_globals(source_list)

