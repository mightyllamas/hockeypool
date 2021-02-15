import cgi
import ConfigParser

import util


def LoadTeamDefinition() :
    teamParser = ConfigParser.SafeConfigParser()
    teamParser.read( 'config/teams.ini' )
    return [MakeTeamDef(teamParser, section) for section in teamParser.sections()]


def MakeTeamDef( teamParser, section ) :
    teamDef = {}
    settings = dict( util.ConvertTuple(x) for x in teamParser.items(section) )
    settings['name'] = cgi.escape( settings['name'] )
    teamDef['settings'] = settings
    teamDef['name'] = section
    players = []
    for playerName in open( 'config/teams/' + section, 'r') :
        splitted = playerName.split( '+' )
        playerName = splitted[0].lower().strip()
        if playerName:
            opts = [x.strip() for x in splitted[1:]]
            players.append( (playerName, opts) )
    teamDef['players'] = players
    return teamDef
