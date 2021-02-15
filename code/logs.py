import datetime
import ConfigParser
import pool
import mailout
import util


def AddChangesToLog( newState, prevState, teamDict, logFn ) :
    logDict = dict( (entry[0],[]) for entry in prevState['logList'] )
    def PostLogMessage( player, msg ) :
        logFn( msg )
        teamName = player.get( 'ifhlteam', 'general' )
        if teamName == 'unsigned' :
            teamName = 'general'
        logDict[teamName].append( msg )

    prevDict = prevState['playerDict']
    oldCap = prevState.get('cap',0)
    newCap = newState['cap']
    if oldCap != newCap :
        PostLogMessage( {}, 'Cap changed from %s to %s (%s)' % (util.Money(oldCap), util.Money(newCap), util.Money(newCap - oldCap)) )
    for name, player in newState['playerDict'].iteritems() :
        niceName = player.get( 'name', name )
        if name not in prevDict :
            logFn( 'player %s created' % niceName )
        else :
            prevPlayer = prevDict[name]
            if player['status'] != prevPlayer['status'] :
                if player['status'] != 'Unsigned' :
                    PostLogMessage( player, '%s signed with %s' % (niceName, player['team']) )
                else :
                    if 'team' in prevPlayer :
                        PostLogMessage( player, '%s released from %s' % (niceName, prevPlayer['team']) )
            prevIFHLTeam = prevPlayer.get( 'ifhlteam', 'unsigned' )
            ifhlTeam = player.get( 'ifhlteam', 'unsigned' )
            if prevIFHLTeam != ifhlTeam :
                if ifhlTeam == 'unsigned' :
                    PostLogMessage( prevPlayer, '%s cut from %s' % (niceName, teamDict[prevIFHLTeam].name) )
                elif prevIFHLTeam == 'unsigned' :
                    PostLogMessage( player, '%s added to %s' % (niceName, teamDict[ifhlTeam].name) )
                else :
                    msg = '%s traded from %s to %s' % (niceName, teamDict[prevIFHLTeam].name, teamDict[ifhlTeam].name)
                    PostLogMessage( player, msg )
                    PostLogMessage( prevPlayer, msg )
            if player.get('position',None) :
                if not pool.FixPositions :
                    if prevPlayer.get('position',None) and player['position'] != prevPlayer['position'] :
                        PostLogMessage( player, '%s changed position from %s to %s' % (niceName, util.PositionNameDict[prevPlayer['position']], util.PositionNameDict[player['position']]) )
                else :
                    try :
                        if player.get('newposition','') :
                            if 'newposition' not in prevPlayer or prevPlayer['newposition'] != player['newposition'] :
                                if pool.Started :
                                    PostLogMessage( player, '%s changed position from %s to %s' % (niceName, util.PositionNameDict[player['position']], util.PositionNameDict[player['newposition']]) )
                                else :
                                    PostLogMessage( player, '%s changed position to %s' % (niceName, util.PositionNameDict[player['position']]) )
                    except :
                        print( repr( player) )
                        raise
            prevSalary = prevPlayer.get('salary', 0)
            currSalary = player.get('salary', 0)
            if prevSalary != currSalary :
                PostLogMessage( player, '%s salary changed from %s to %s (%s)' % (niceName, util.Money(prevSalary), util.Money(currSalary), util.Money(currSalary - prevSalary)) )

    filterDate = util.TodaysDate - datetime.timedelta(30)
    def FixLogEntries( name, list ) :
        newList = [x for x in list if filterDate < x[0]]
        if logDict[name] != [] :
            newList.append( (util.TodaysDate, logDict[name]) )
        newList.sort( key=lambda x:x[0], reverse=True )
        return newList
    return [(name,FixLogEntries(name, list)) for name, list in prevState['logList']]


def FindRecentCapChanged( logList ) :
    for team, dayList in logList :
        if team == 'general' :
            for date, eventList in dayList :
                for event in eventList :
                    if event.startswith( 'Cap changed' ) :
                        return [(date, [event])]
    return []


def GetRecentLogs( logList ) :
    latestEvents = [dayList[0] for team, dayList in logList if team != 'general' and dayList != []]
    latestEvents += FindRecentCapChanged( logList )
    if latestEvents == [] :
        return None
    latestEvents.sort( key=lambda x:x[0], reverse=True )
    newest = [latestEvents[0][0], latestEvents[0][1][:]]
    for more in latestEvents[1:] :
        if more[0] != newest[0] :
            break
        newest[1] += more[1]
    uniqued = set(newest[1])
    newest[1] = list(uniqued)
    return newest


def MailLogs( poolState ) :
    teamParser = ConfigParser.SafeConfigParser()
    teamParser.read( 'config/teams.ini' )
    mailTo = dict( (x,[]) for x in teamParser.sections() if teamParser.has_option(x,'mailstatus') and teamParser.getboolean(x,'mailstatus') )

    logList = poolState['logList']
    for team, dayList in logList :
        if team != 'general' and dayList != [] and team in mailTo :
            if dayList[0][0] == util.TodaysDate :
                mailTo[team] += dayList[0][1]
    capChanged = FindRecentCapChanged( logList )
    if capChanged[0] == util.TodaysDate :
        for team in mailTo.iterkeys() :
            mailTo[team] += capChanged[1]

    for team, msgs in mailTo.iteritems() :
        if msgs :
            subject = 'IFHL News for %s on %s' % (teamParser.get(team,'name'), util.TodaysDate.isoformat())
            msgBody = '\n'.join( ' * %s\n' % x for x in msgs )
            msg = '%s\n\n%s\n' % (subject, msgBody)
            for name, value in teamParser.items( team )  :
                if name.startswith( 'email' ) :
                    mailout.SendMsg( value, subject, msg )
