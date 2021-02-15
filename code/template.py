import os
import sys
import StringIO
from mako.template import Template
from mako.runtime import Context

import util

MakoModuleDir = 'data/mako_modules'
MainDir = os.path.dirname(os.path.dirname(sys.argv[0]))
SiteDir = 'site/'

def Init() :
    util.Mkdir( MakoModuleDir )


def DoTemplateSubstitution( templateName, pageName, args, doPlain=True, doPrintable=False ) :
    versions = [('','<br>')]
    if doPlain :
        versions.append(('plain','&nbsp;&nbsp;'))
    if doPrintable :
        versions.append( ('printable', '&nbsp;&nbsp;') )
    for prefix, spacer in versions :
        try :
            args['prefix'] = prefix
            args['spacer'] = spacer
            frontTemplate = Template( filename=os.path.abspath(MainDir+'/template/' + templateName), module_directory=MakoModuleDir )
            tmpFile = StringIO.StringIO()
            context = Context(tmpFile, **args )
            frontTemplate.render_context(context)
            withTabs = tmpFile.getvalue().replace( '        ', '\t' )
            destFile = open( SiteDir + prefix + pageName , 'w' )
            destFile.write( withTabs )
            destFile.close()
        except :
            print( "error generating " + prefix + pageName )
            raise


