import xml.etree.ElementTree as ET
import util

def WriteData( source, data ) :
    util.Mkdir( 'xml' )
    topLevel = ET.Element( source )
    for entry in data :
        player = ET.SubElement( topLevel, 'player' )
        for key, value in entry.iteritems() :
            curr = ET.SubElement( player, key )
            curr.text = str(value)
    tree = ET.ElementTree( topLevel )
    tree.write( 'xml/%s.xml' % source )

