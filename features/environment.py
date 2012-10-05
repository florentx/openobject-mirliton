# -*- coding: utf-8 -*-
import erppeek

from support import tools, behave_better

__all__ = []
OPENERP_ARGS = '-c etc/openerp-server.conf --without-demo all'
OPENERP_ARGS += ' --logfile var/log/behave-stdout.log'

# Print readable 'Fault' errors
tools.patch_traceback()
# Some monkey patches to enhance Behave
behave_better.patch_all()


def before_all(ctx):
    server = erppeek.start_openerp_services(OPENERP_ARGS)
    admin_passwd = server.tools.config['admin_passwd']
    database = server.tools.config['db_name']
    ctx._is_context = True
    ctx.client = erppeek.Client(server, verbose=ctx.config.verbose)
    ctx.conf = {
        'server': server,
        'admin_passwd': admin_passwd,
        'db_name': database,
    }


def before_feature(ctx, feature):
    ctx.data = {}


def before_step(ctx, step):
    ctx._messages = []
    # Extra cleanup (should be fixed upstream?)
    ctx.table = None
    ctx.text = None


def after_step(ctx, laststep):
    if ctx._messages:
        # Flush the messages collected with puts(...)
        output = ctx.config.output
        for item in ctx._messages:
            for line in str(item).splitlines():
                output.write(u'      %s\n' % (line,))
        # output.flush()
    if laststep.status == 'failed' and ctx.config.stop:
        # Enter the interactive debugger
        tools.set_trace()
