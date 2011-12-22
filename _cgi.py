
import cgi
import cgitb
cgitb.enable()

class ErrorContext(object):
    def __enter__(self):
        import sys
        self._se = sys.stderr
        import StringIO
        self.io = StringIO.StringIO()
        sys.stderr = self.io

    def __exit__(self, ex, ex1, ex2):
        import sys
        sys.stderr = self._se
        if ex and not isinstance(ex, SystemExit):
            data = self.io.getvalue()
            try:
                ex.stderr = data
            except: pass

with ErrorContext():
    import explorer
    explorer.main()
