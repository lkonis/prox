class SP:
    path_list = [(r'..', True)]

    def __init__(self):
        print 'try once append'
        self.path_list.append((r'..\\', False))

    def search_full_path(self, fname):
        print 'return full path'
        fp = ''
        return fp



