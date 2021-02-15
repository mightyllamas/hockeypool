import copy
import glob
import itertools
import os
import shutil
import sys
import datetime

import logs
import pool
import util
import template
import player

exec 'import ruleset.%s as ruleset' % pool.RuleSet in globals()

LogFile = None

def Init() :
    template.Init()
    util.Mkdir( 'site' )
    util.Mkdir( 'site/logos' )
    util.Mkdir( 'site/jerseys' )
    util.Mkdir( 'site/teams' )
    util.Mkdir( 'site/unsigned' )
    util.Mkdir( 'site/summary' )
    util.Mkdir( 'site/history' )
    util.Mkdir( 'site/draft' )
    util.Mkdir( 'site/printableteams' )
    util.Mkdir( 'site/plainteams' )
    util.Mkdir( 'site/plainunsigned' )
    util.Mkdir( 'site/plainsummary' )
    util.Mkdir( 'site/players' )
    util.Mkdir( 'site/plainplayers' )
    util.Mkdir( 'site/plainhistory' )
    util.Mkdir( 'site/plaindraft' )
    global LogFile
    LogFile = open( 'log/webwriter.log', 'w' )
    LogFile.write( 'weblog starting %s\n' % datetime.datetime.today().isoformat() )

def Fini() :
    LogFile.write( 'weblog finished %s\n' % datetime.datetime.today().isoformat() )
    LogFile.close()

def Log( x ) :
    LogFile.write( x + '\n' )

def Error( x ) :
    x = 'Error: ' + x
    print x
    Log( x )
    raise Exception(x)

AdjustDict = {}
def ReadAdjustDict() :
    if os.path.exists( 'config/adjust.py' ) :
        global AdjustDict
        f = open('config/adjust.py', 'r')
        AdjustDict = eval( f.read() )
        f.close()


def ExpectedGames( pos, gamesCounting ) :
    if pos == 'g' :
        return gamesCounting
    elif pos == 'd' :
        return gamesCounting * 4
    return gamesCounting*3


def SumStats( playerName, dailyData, startDate, endDate ) :
    totalStats = dict( (x,0) for x in util.StatsFields )
    lastUpdate = datetime.date.min
    for date, stats in dailyData :
        if date > startDate and date <= endDate :
            if playerName in stats :
                lastUpdate = date
                currDay = stats[playerName]
                for x in util.StatsFields :
                   if x in currDay :
                        totalStats[x] += currDay[x]
    if playerName in AdjustDict :
        adjustEntry = AdjustDict[playerName]
        for x in util.StatsFields :
            if x in adjustEntry :
                totalStats[x] -= adjustEntry[x]
    return totalStats, lastUpdate


class TeamInfo :
    def __init__( self, teamData, data, dailyData, schedule, nhlRemaining ) :
        self.scalelogo = False
        self.unofficial = 0
        self.__dict__.update( teamData['settings'] )
        self.section = teamData['name']
        self.roster = util.MakeListByPosition()
        self.scoring = util.MakeListByPosition()
        self.previous = util.MakeListByPosition()
        self.predicted = util.MakeListByPosition()
        self.todayPrediction = util.MakeListByPosition()
        playedYesterday = set()
        if pool.UsesSchedule and pool.Started :
            for d,t1,t2 in schedule :
                if d == util.YesterdaysDate :
                    playedYesterday.add(t1)
                    playedYesterday.add(t2)
        self.emptySpots = 22
        self.contract = {'unknown':0, 'RFA':0, 'UFA':0, 'raises':0.0}
        for playerName, opts in teamData['players'] :
            if playerName not in data :
                Error( "player %s not found, team %s" % (playerName, teamData['name']) )
            playerDict = data[playerName]
            startDate = datetime.date.min
            endDate = datetime.date.max
            posOverride = None
            extraOpts = set()
            for opt in opts :
                cmd = opt.split()
                if cmd[0].startswith( 'start' ) :
                    startDate = util.ParseDate( cmd[1] )
                elif cmd[0].startswith( 'end' ) :
                    endDate = util.ParseDate( cmd[1] )
                elif cmd[0].startswith( 'pos' ) :
                    posOverride = cmd[1]
                else :
                    extraOpts.add( cmd[0] )

            if endDate == datetime.date.max : 
                if self.unofficial == 0 :
                    playerDict['ifhlteam'] = self.section
                self.emptySpots -= 1
            if posOverride :
                playerDict = copy.copy(playerDict)
                if not playerDict.get('newposition', '') :
                    playerDict['newposition'] = playerDict['position']
                playerDict['position'] = posOverride
            playerDict['extraOpts'] = extraOpts
            lastStats = None
            stats = None
            fullStats = None
            lastGame = datetime.date.min
            if 'nhlname' in playerDict :
                playerName = playerDict['nhlname']
                stats, lastGame = SumStats( playerName, dailyData, startDate, endDate )
                fullStats = stats
                if endDate == datetime.date.max :
                    lastStats = dailyData[-1][1].get( playerName, None )
                if startDate != datetime.date.min :
                    fullStats, earlyGame = SumStats( playerName, dailyData, datetime.date.min, startDate )
                    for x in util.StatsFields :
                        fullStats[x] += stats[x]
                    lastGame = max( lastGame, earlyGame )
            info = player.PlayerInfo( playerDict, stats, lastStats )
            pos = playerDict['position']
            if not pos : 
                print( playerDict )
            self.scoring[pos].append( info )
            if endDate == datetime.date.max :
                rosterPlayer = info
                if fullStats != stats :
                    rosterPlayer = player.PlayerInfo( playerDict, fullStats, lastStats )
                    info.roster = rosterPlayer
                self.roster[pos].append( rosterPlayer )
                if rosterPlayer.contract :
                    nextYear = rosterPlayer.contract[1]
                    if nextYear == 'RFA' :
                        self.contract['RFA'] += 1
                    elif nextYear == 'UFA' :
                        self.contract['UFA'] += 1
                    elif util.IsNumeric( nextYear ) :
                        self.contract['raises'] += float(nextYear) - rosterPlayer.salary
                    else :
                        self.contract['unknown'] += 1
                else :
                    self.contract['unknown'] += 1
                t = rosterPlayer.team
                if pool.UsesSchedule and pool.Started :
                    missingGames = sum(1 for d, g1, g2 in schedule if d < util.TodaysDate and d > lastGame and (t==g1 or t==g2))
                    if missingGames > 0 :
                        rosterPlayer.decoraters.append( str(missingGames) )
                        if rosterPlayer != info :
                            info.decoraters.append( str(missingGames) )
                    if fullStats and info.team != 'Unsigned' :            
                        predStats = copy.copy( stats )
                        teamRemain = nhlRemaining[info.team]
                        fgp = float(fullStats['gamesplayed'])
                        if (missingGames > 0 or pos == 'g') and teamRemain < util.SeasonLength(schedule)  :
                            deltaPlayed = round( fgp / (util.SeasonLength(schedule) - teamRemain) * teamRemain, 0 )
                        else :
                            deltaPlayed = float(teamRemain)
                        predStats['points'] += util.CalcPPG(fullStats['points'], fullStats['gamesplayed']) * deltaPlayed
                        predStats['gamesplayed'] += deltaPlayed
                        if playerDict['position'] == 'g' and fgp > 0 :
                            predStats['shots'] += fullStats['shots'] / fgp * deltaPlayed
                            predStats['saves'] += fullStats['saves'] / fgp * deltaPlayed
                            predStats['minutes'] += fullStats['minutes'] / fgp * deltaPlayed
                        self.predicted[pos].append( player.PlayerInfo( playerDict, predStats, None ) )
            else :
                info.ghost = True
                info.decoraters.append( 'X' )
                self.predicted[pos].append( copy.copy(info) )
            if startDate != util.TodaysDate :
                prevStats = stats
                if lastStats :
                    prevStats = dict( (x, (stats[x] - lastStats[x])) for x in lastStats.iterkeys() )
                self.previous[pos].append( player.PlayerInfo( playerDict, prevStats, None ) )
                todayPredict = prevStats
                if not info.ghost and fullStats and info.team in playedYesterday :
                    isInjured = (player != 'g' and missingGames > 0) or missingGames > 2
                    if not isInjured :
                        todayPredict = copy.copy( todayPredict )
                        todayPredict['points'] += util.CalcPPG(fullStats['points'], fullStats['gamesplayed'])
                        fgp = float(fullStats['gamesplayed'])
                        if playerDict['position'] == 'g' and fgp > 0 :
                            todayPredict['shots'] += fullStats['shots'] / fgp
                            todayPredict['saves'] += fullStats['saves'] / fgp
                            todayPredict['minutes'] += fullStats['minutes'] / fgp
                        todayPredict['gamesplayed'] += 1
                self.todayPrediction[pos].append( player.PlayerInfo( playerDict, todayPredict, None ) )
       
        self.salary = sum( sum( p.salary for p in list ) for list in self.roster.itervalues() )
        ruleset.ParseTeamData( self )

        for pos, playerList in self.roster.iteritems() :
            playerList.sort( key=player.GetPlayerKey, reverse=True )
        self.stats = {}
        if pool.UsesSchedule and pool.Started :
            inNHL = [x for posList in self.roster.itervalues() for x in posList if x.team in nhlRemaining]
            self.gamesLeft = round( sum(nhlRemaining[x.team] for x in inNHL) / float(len(inNHL)), 1 )
        else :
            self.gamesLeft = 82


    def ComputePoints( self, playerDict, gamesCounting, smallpuckGAA ) :
        points = 0
        gamesMissing = {}
        for pos, playerList in playerDict.iteritems() :
            gamesLeft = ExpectedGames( pos, gamesCounting )
            if pos == 'g' :
                def GoaliePoints( x, gp ) :
                    pts = gp * (-x.gaa)
                    if gp > 0 :
                        pts += x.p
                    return pts
                calcPoints = GoaliePoints
            else :
                calcPoints = lambda x,g : g*x.ppg
            playerList.sort( key=player.GetPlayerKey, reverse=True )
            for playerObj in playerList :
                if gamesLeft < playerObj.gp :
                    playerObj.pc = calcPoints(playerObj, gamesLeft)
                    points += playerObj.pc
                    playerObj.gc = gamesLeft
                    gamesLeft = 0
                    break
                playerObj.pc = calcPoints(playerObj, playerObj.gp)
                points += playerObj.pc
                gamesLeft -= playerObj.gp
                playerObj.gc = playerObj.gp
            gamesMissing[pos] = gamesLeft
            if pos == 'g' :
                points -= gamesLeft * (smallpuckGAA + 2)
        return round(points, 1), gamesMissing

    def AddGhosts( self, gamesMissing, smallpuck, prevMissing, prevSmallpuck ) :
        for pos, missing in gamesMissing.iteritems() :
            if missing > 0 :
                if pos == 'g' :
                    gaa = smallpuck.gaa + 2
                    dummyStats  = {'gamesplayed':missing,'shots':gaa * 100, 'saves':0, 'minutes':60*100, 'points':round(-gaa * missing, 1)}
                    prevSmallpuck += 2
                    oldMiss = prevMissing[pos]
                    prevDummy = {'gamesplayed':oldMiss, 'shots':prevSmallpuck, 'saves':0, 'minutes':60*100, 'points':round(-prevSmallpuck * oldMiss,1)}
                    ghost = self.AddGhost( 'Joe Smallpuck', 'g', dummyStats, prevDummy )
                else :
                    ghost = self.AddGhost( '%s Plumber' % util.FunnyNames[pos], pos, {'gamesplayed':missing,'points':0}, {'gamesplayed':prevMissing[pos], 'points':0} )
                ghost.pc = ghost.p
                ghost.gc = ghost.gp

    def AddGhost( self, name, position, stats, prevStats ) :
        dummyPlayer = {'name':name, 'keyname':name, 'status':'Signed', 'ifhlteam':self.section, 'position':position, 'team':'Petrolia Plumbers'}
        ghostPlayer = player.PlayerInfo( dummyPlayer, stats, prevStats )
        self.scoring[position].append( ghostPlayer )
        return ghostPlayer

    def AddTotals( self ) :
        for pos, playerList in self.scoring.iteritems() :
            numPlayers = len(playerList)
            newPlayer = self.AddGhost( 'Total ' + util.PositionNameDict[pos], pos, None, None )
            newPlayer.salary = 0
            for oldPlayer in playerList :
                if oldPlayer != newPlayer :
                    newPlayer.gp += oldPlayer.gp
                    newPlayer.dgp += oldPlayer.dgp
                    newPlayer.p += oldPlayer.p
                    newPlayer.dp += oldPlayer.dp
                    newPlayer.gc += oldPlayer.gc
                    newPlayer.dgc += oldPlayer.dgc
                    newPlayer.pc += oldPlayer.pc
                    newPlayer.dpc += oldPlayer.dpc
                    newPlayer.salary += oldPlayer.salary
                    newPlayer.age += oldPlayer.age
                    newPlayer.fog += oldPlayer.fog
                    if pos == 'g' :
                        newPlayer.shots += oldPlayer.shots
                        newPlayer.saves += oldPlayer.saves
                        newPlayer.minutes += oldPlayer.minutes
                if oldPlayer.roster :
                    oldPlayer.roster.gc = oldPlayer.gc
                    oldPlayer.roster.dgc = oldPlayer.dgc
                    oldPlayer.roster.pc = oldPlayer.pc
                    oldPlayer.roster.dpc = oldPlayer.dpc
            if pos == 'g' :
                newPlayer.gaa = util.CalcGAA( newPlayer.shots, newPlayer.saves, newPlayer.minutes )
                newPlayer.savepercent = util.CalcSavePercent( newPlayer.saves, newPlayer.shots )
            else :
                newPlayer.ppg = util.CalcPPG( newPlayer.pc, newPlayer.gc )
                newPlayer.dppg = newPlayer.ppg - util.CalcPPG( newPlayer.pc - newPlayer.dpc, newPlayer.gc - newPlayer.dgc )
            newPlayer.salaryFancy = util.Money( newPlayer.salary )
            newPlayer.nhlPosition = pos
            newPlayer.age = 0 if numPlayers == 0 else round( newPlayer.age / numPlayers, 1 )
            newPlayer.team = self.name
            newPlayer.fog = 0 if numPlayers == 0 else newPlayer.fog / numPlayers

    def CalcDeltaScoring( self ) :
        if not pool.Started :
            return
        for pos, playerList in self.scoring.iteritems() :
            for player in playerList :
                for prev in self.previous[util.TidyPosition(pos)] :
                    if prev.name == player.name :
                        player.dgc = player.gc - prev.gc
                        player.dpc = player.pc - prev.pc
                        break

    def FinishStats( self, gamesCounting ) :
        self.stats['gp'] = 0
        self.stats['pc'] = 0
        self.stats['age'] = 0
        totalKnownAge = 0
        for pos, playerList in self.roster.iteritems() :
            self.stats[pos] = {}
            numPlayers = len(playerList)
            self.stats[pos]['number'] = numPlayers
            self.stats[pos]['age'] = sum( x.age for x in playerList )
            totalSalary = sum( x.salary for x in playerList )
            self.stats[pos]['$salary'] = totalSalary
            self.stats[pos]['$avgsal'] = 0 if numPlayers == 0 else round( totalSalary / float(numPlayers), 0 )
            self.stats['age'] += self.stats[pos]['age']
            numKnownAge = sum( 1 for x in playerList if x.age > 0 )
            totalKnownAge += numKnownAge
            self.stats[pos]['age'] = 0 if numKnownAge == 0 else round( self.stats[pos]['age'] / float(numKnownAge), 1 )
        for pos, playerList in self.scoring.iteritems() :
            self.stats[pos]['gp'] = sum( x.gp for x in playerList ) - ExpectedGames( pos, gamesCounting )
            self.stats[pos]['pc'] = round( sum(x.pc for x in playerList), 1 )
            for stat in ['gp','pc'] :
                self.stats[stat] += self.stats[pos][stat]
        numPlayers = 22 - self.emptySpots
        self.stats['number'] = numPlayers
        if totalKnownAge == 0 : # hack fix
            self.stats['age'] = 1
        else :
            self.stats['age'] = round( self.stats['age'] / float(totalKnownAge), 1 )
        self.stats['$salary'] = self.salary
        self.stats['$avgsal'] = round( self.salary / float(numPlayers), 0 )

    def GetStat( self, statName, prefix ) :
        statDict = self.stats
        splitName = statName.split('-')
        if len(splitName) == 2 :
            statDict = self.stats[splitName[1]]
        statName = splitName[0]
        statVal = statDict[statName]
        if statName[0] == '$' and prefix == 'plain' :
            return util.Money(statVal)
        return statVal


def MakeTeamList( teamData, dataDict, dailyData, prevTotal, schedule, cap, gamesCounting ) :
    nhlRemaining = 0
    if pool.UsesSchedule and pool.Started :
        nhlRemaining = dict( (x[1], sum(1 for d, g1, g2 in schedule if d >= util.TodaysDate and (x[1]==g1 or x[1]==g2))) for x in util.TeamNames )
    teamList = [TeamInfo(x, dataDict, dailyData, schedule, nhlRemaining) for x in teamData]
    smallpuck = ruleset.ComputeScoring( teamList, dataDict, dailyData, prevTotal, schedule, cap, gamesCounting )
    if pool.Started :
        prevSort = lambda x:x.prevPoints
        currSort = lambda x:x.points
    else :
        def MapLastYear( finish ) :
            if finish <= 6 :
                return 7 - finish
            if finish == 13 :
                return -1
            return 0
        prevSort = lambda x:x.poolpoints - MapLastYear(x.lastyear)
        currSort = lambda x:x.poolpoints
    teamList.sort( key=prevSort, reverse=True )
    for team, rank in itertools.izip( teamList, itertools.count(1) ) :
        team.prevRank = rank
    teamList.sort( key=currSort, reverse=True )
    for team, rank in itertools.izip( teamList, itertools.count(1) ) :
        team.rank = rank
        team.deltaRank = team.prevRank - rank
    officialList = [x for x in teamList if not x.unofficial]
    for team, rank in itertools.izip( officialList, itertools.count(1) ) :
        team.officialRank = rank
    return teamList, smallpuck


def MakeNewRosterPages( teamList ) :
    forwardStats = ['GP','dGP', 'P', 'dP', 'PPG', 'dPPG', 'GC', 'dGC', 'PC', 'dPC', 'FOG', 'Salary', 'Age', 'Team']
    forwardHdrs  = [('GP',1), ('+',1), ('P',1), ('+',1), ('PPG',3), ('+',5), ('GC', 6), ('+', 6), ('PC',6), ('+',6),
                    ('FOG',6), ('Salary',4), ('Age',4), ('Team',6)]
    goalieStats = ['GP','dGP', 'GAA', 'dGAA', 'P', 'W', 'Sv', 'GC', 'dGC', 'PC', 'dPC', 'Salary', 'Age', 'Team']
    goalieHdrs = [('GP',1), ('+',1), ('GAA',1), ('+',1), ('P', 6), ('W', 6), ('Sv%', 6), ('GC', 6), ('+', 6), ('PC',6), ('+',6),
                    ('Salary',4), ('Age',4), ('Team',6)]
    forwardInfo = {'stats':forwardStats, 'header':forwardHdrs}
    goalieInfo = {'stats':goalieStats, 'header':goalieHdrs}
    positions = util.PositionNameDict.items()
    positionInfo = {'forward' : forwardInfo, 'goalie' : goalieInfo}
    subsDict = {'teams':teamList,
                'posInfo' : positionInfo,
                'positions' : positions,
                'pool' : pool.__dict__,
                'draftYear' : pool.GetDraftYear(),
                }
    for team in teamList :
        subsDict['team'] = team
        subsDict['roster'] = team.scoring
        subsDict['teamname'] = team.name
        template.DoTemplateSubstitution( 'roster.html', 'teams/%s_new.html' % (team.section), subsDict, doPlain=False, doPrintable=False )

def MakeRosterPages( teamList ) :
    baseForwardStats = ['GP','dGP','P','dP','PPG','dPPG']
    baseGoalieStats = ['GP','dGP','GAA','dGAA', 'W', 'Sv%']
    forwardInfo = {'stats':baseForwardStats, 'key':'PPG', 'dir':'desc' }
    positions, positionInfo, rosters, rosterFn = ruleset.ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo )

    subsDict = {'teams':teamList,
                'posInfo' : positionInfo,
                'positions' : positions,
                'pool' : pool.__dict__,
                'draftYear' : pool.GetDraftYear(),
                'rosterType':'main'}
    teamList.sort( key=lambda x:x.name )
    def GenPages( getRoster ) :
        subsDict['otherRosters'] = [x for x in rosters if x != subsDict['rosterType']]
        for team in teamList :
            subsDict['team'] = team
            subsDict['roster'] = getRoster( team )
            subsDict['teamname'] = team.name
            template.DoTemplateSubstitution( 'rosterpage.html', 'teams/%s_%s.html' % (team.section, subsDict['rosterType']), subsDict, True )
    GenPages( rosterFn )
    if 'score' in rosters :
        subsDict['rosterType'] = 'score'
        forwardInfo['stats'] = ['GP','GC','dGC','P','dP','PC','dPC','PPG']
        positionInfo['g']['stats'] = ['GP','GC','dGC','GAA','dGAA','PC','dPC']
        GenPages( lambda x:x.scoring )
    if 'predicted' in rosters :
        subsDict['rosterType'] = 'predicted'
        forwardInfo['stats'] = ['GP','GC','dGC','P','dP','PC','dPC','PPG']
        positionInfo['g']['stats'] = ['GP','GC','dGC','GAA','dGAA','PC','dPC']
        GenPages( lambda x:x.predicted )
    if 'wide' in rosters :
        subsDict['rosterType'] = 'wide'
        forwardInfo['stats'] = baseForwardStats + ['GC','dGC','PC','dPC', 'FOG', 'Salary', 'Age', 'Team']
        positionInfo['g']['stats'] = baseGoalieStats + ['GC','dGC','PC','dPC', 'Salary', 'Age', 'Team']
        GenPages( lambda x:x.roster )
    if 'extra' in rosters :
        subsDict['rosterType'] = 'extra'
        forwardInfo['stats'] = ['GP', 'P', 'PPG', 'FOG', 'Salary', 'Age', 'Team']
        positionInfo['g']['stats'] = baseGoalieStats + ['Salary', 'Age', 'Team']
        GenPages( lambda x:x.roster )
    if 'salary' in rosters :
        subsDict['rosterType'] = 'salary'
        forwardInfo['stats'] =  [str(pool.PoolYear + x) for x in range(0,6)]  + ['Age', 'Team']
        forwardInfo['key'] = 'name'
        forwardInfo['dir'] = 'asc'
        positionInfo['g']['stats'] = forwardInfo['stats']
        positionInfo['g']['key'] = 'name'
        positionInfo['g']['dir'] = 'asc'
        GenPages( lambda x:x.roster )
    if 'trading' in rosters:
        subsDict['rosterType'] = 'trading'
        thisYear = str(pool.PoolYear)
        nextYear = str(pool.PoolYear + 1)
        yearAfter = str(pool.PoolYear + 2)
        forwardInfo['stats'] = ['GP','P','PPG',thisYear,nextYear,yearAfter,'Age','Team']
        positionInfo['g']['stats'] = ['GP','P','GAA',thisYear,nextYear,yearAfter,'Age','Team']
        GenPages( lambda x:x.roster )


def MakeTeamStatPages( teamList ) :
    summaryStats = ['games', 'points', 'age', 'number', 'salary']
    summaryTitles = [(x, x.capitalize()) for x in summaryStats]
    pages = util.PositionNameDict.items() + summaryTitles
    subsDict = {'teamList':teamList, 'sortKey':'pc', 'pages':pages}
    def GenPages( headers, statList, pageName, fancyName ) :
        subsDict['headers'] = headers
        subsDict['statList'] = statList
        subsDict['fancyName'] = fancyName
        template.DoTemplateSubstitution( 'teamsummary.html', 'summary/%s.html' % pageName, subsDict )
    headers = ['GP', 'PC', 'Age', '#', 'Salary', 'Avg$']
    statsBase = ['gp', 'pc', 'age', 'number', '$salary', '$avgsal']
    for pos, fancyName in util.PositionNameDict.iteritems() :
        statsList = ['%s-%s' % (x,pos) for x in statsBase]
        subsDict['sortKey'] = 'pc-' + pos
        teamList.sort( key=lambda x:x.stats[pos]['pc'], reverse=True )
        GenPages( headers, statsList, pos, fancyName )
    getKeys = util.PositionNameDict.iterkeys
    for index, titles in itertools.izip( itertools.count(), summaryTitles ) :
        mainStat = statsBase[index]
        subsDict['sortKey'] = mainStat
        statsList = [mainStat] + ['%s-%s'%(mainStat,x) for x in getKeys()] + statsBase[:index] + statsBase[index+1:]
        mainHead = headers[index]
        headerList = [mainHead] + [x.upper() for x in getKeys()] + headers[:index] + headers[index+1:]
        teamList.sort( key=lambda x:x.stats[mainStat], reverse=True )
        GenPages( headerList, statsList, titles[0], titles[1] )


def MakeRankingPages( dataDict, teamDict, seasonStats, gamesCounting ) :
    n = 40
    gp = min( 5, gamesCounting )
    playersByPos = util.MakeListByPosition()
    for playerDict in dataDict.itervalues() :
        if 'nhlname' in playerDict :
            nhlName = playerDict['nhlname']
            if nhlName in seasonStats :
                stats = seasonStats[nhlName]
                try :
                    if stats['gamesplayed'] >= gp :
                        p = player.PlayerInfo(playerDict, stats)
                        playersByPos[p.position].append( p )
                except :
                    print( playerDict )
                    raise
    subsDict = {'n':n, 'gp':gp, 'abbrevDict' : util.TeamAbbrevs, 'teamDict' : teamDict, 'sortKey': 'ppg'}
    for pos in playersByPos.iterkeys() :
        subsDict['plainPos'] = pos
        subsDict['fancyPos'] = util.PositionNameDict[pos]
        if pos == 'g' :
            getPPG = lambda x:x.gaa
            subsDict['mainStat'] = 'GAA'
            subsDict['sortDir'] = 'asc'
        else :
            getPPG = lambda x:-x.ppg
            subsDict['mainStat'] = 'PPG'
            subsDict['sortDir'] = 'desc'
        players = [x for x in playersByPos[pos] if x.ifhlteam == 'unsigned']
        def GeneratePages( playList, pageName ) :
            playList.sort( key=getPPG )
            subsDict['players'] = playList[:n]
            subsDict['pageName'] = pageName.capitalize()
            subsDict['positions'] = util.PositionNameDict.items()
            template.DoTemplateSubstitution( 'unsigned.html', '%s/%s.html' % (pageName, pos), subsDict )
        GeneratePages( players, 'unsigned' )


def MakeYoungGunsPages( dataDict, teamDict, seasonStats ) :
    playersByPos = { 'f':[], 'd':[] }
    posNameDict = { 'f':'Forward', 'd':'Defence' }
    cutoffDate = datetime.date( util.TodaysDate.year - 25, 10, 1 )
    for playerDict in dataDict.itervalues() :
        if 'nhlname' in playerDict and ('birthdate' not in playerDict or playerDict['birthdate'] > cutoffDate) :
            nhlName = playerDict['nhlname']
            if nhlName in seasonStats :
                stats = seasonStats[nhlName]
                pos = playerDict['position']
                if pos == 'd' :
                    playersByPos['d'].append( player.PlayerInfo(playerDict, stats) )
                elif pos != 'g' :
                    playersByPos['f'].append( player.PlayerInfo(playerDict, stats) )
    subsDict = {'gp':-1, 'abbrevDict' : util.TeamAbbrevs, 'teamDict' : teamDict, 'sortKey': 'ppg'}
    for pos in playersByPos.iterkeys() :
        subsDict['plainPos'] = pos
        subsDict['fancyPos'] = posNameDict[pos]
        getPPG = lambda x:-x.ppg
        subsDict['mainStat'] = 'PPG'
        subsDict['sortDir'] = 'desc'
        players = [x for x in playersByPos[pos] if x.ifhlteam == 'unsigned']
        def GeneratePages( playList, pageName ) :
            playList.sort( key=getPPG )
            subsDict['players'] = playList
            subsDict['pageName'] = pageName.capitalize()
            subsDict['positions'] = posNameDict.items()
            template.DoTemplateSubstitution( 'unsigned.html', '%s/%s.html' % (pageName, pos), subsDict )
        GeneratePages( players, 'unsigned' )


def GetSeasonMonths( year ) :
    currMonth  = 10
    currYear = year - 1
    while currMonth <= 12 :
        yield datetime.date( currYear, currMonth, 1 )
        currMonth += 1
    currYear += 1
    currMonth = 1
    while currMonth <= 5 :
        yield datetime.date( currYear, currMonth, 1 )
        currMonth += 1


def CalcSplits( player, year, dailyData ) :
    splits = []
    if not player.nhlname :
        return splits
    name = player.nhlname
    allMonths = GetSeasonMonths( year )
    startDate = allMonths.next()
    initialDate = startDate
    for endDate in allMonths :
        stats = SumStats( name, dailyData, startDate, endDate )[0]
        if stats['gamesplayed'] > 0 :
            splits.append( (startDate.strftime('%B %Y'), startDate.isoformat(), year, stats ) )
        startDate = endDate
        if endDate > util.TodaysDate :
            break
    if splits :
        splits.append( ("Total %d" % year, '~', year, SumStats( name, dailyData, initialDate, startDate )[0]) )
    return splits


def MakeAllPlayersPage( dataDict, teamDict, seasonStats, dailyData, prevDaily ) :
    subsDict = {'util': util, 'teamDict' : teamDict, 'pool':pool}
    allPlayers = [player.PlayerInfo(p, seasonStats.get(p.get('nhlname',"z"),None)) for p in dataDict.itervalues() if p.get('position',None) and p.get('position',None) != 'g']
    allPlayers.sort( key=lambda x:-x.ppg )
    subsDict['players'] = allPlayers
    subsDict['pageName'] = 'Skaters'
    subsDict['sortDir'] = 'desc'
    subsDict['mainStat'] = 'PPG'
    template.DoTemplateSubstitution( 'allplayers.html', 'allskaters.html', subsDict )
    def GenPlayerPages( playerList ) :
        for playerObj in playerList :
            monthlySplits = []
            for year, dailyStats in prevDaily :
                monthlySplits += CalcSplits( playerObj, year, dailyStats )
            monthlySplits += CalcSplits( playerObj, pool.PoolYear + pool.Started - 1, dailyData )
            subsDict['player'] = playerObj
            subsDict['splits'] = monthlySplits
            template.DoTemplateSubstitution( 'player.html', playerObj.dataFileName, subsDict )
    GenPlayerPages( allPlayers )
    allPlayers = [player.PlayerInfo(p, seasonStats.get(p.get('nhlname',"z"),None)) for p in dataDict.itervalues() if 'position' in p and p['position'] == 'g']
    allPlayers.sort( key=lambda x:x.gaa )
    subsDict['players'] = allPlayers
    subsDict['pageName'] = 'Goalies'
    subsDict['sortDir'] = 'asc'
    subsDict['mainStat'] = 'GAA'
    template.DoTemplateSubstitution( 'allplayers.html', 'allgoalies.html', subsDict )
    GenPlayerPages( allPlayers )


def MakeLogPage( logList, teamList ) :
    teamDict = dict( (team.section, team.name) for team in teamList )
    teamDict['general'] = 'League News'
    def LogSort(x) :
        if x[0] == 'general' :
            return 'A'   # want this sorting first
        return teamDict[x[0]]
    logList.sort( key=LogSort )
    template.DoTemplateSubstitution( 'news.html', 'news.html', {'logs':logList, 'teamDict':teamDict} )


def MakeDraftPages( teamList, teamDict, playerDict, dailyData ) :
    teamList = [x for x in teamList if x.unofficial == 0]
    draftFiles = glob.glob( 'config/drafts/*.txt' )
    years = {}
    for fileName in draftFiles :
        year = int(fileName[-8:-4])
        picks = []
        round = []
        for line in open( fileName, 'r' ) :
            line = line.strip()
            if not line :
                continue
            if line.startswith( '--' ) :
                picks.append( round )
                round = []
            else :
                team, playerName = line.split( ',', 1 )
                if team not in teamDict :
                    Error( "unknown team: %s in file %s" % (team, fileName) )
                playerName = playerName.strip().lower()
                if playerName not in playerDict :
                    round.append( (team, playerName.title(), None, None) )
                else :
                    playerData = playerDict[playerName]
                    round.append( (team, playerData['name'], player.MakePlayerFileName(playerName),playerData) )
        picks.append( round )
        years[year] = picks

    def MakeDraftPickList( year, getter, ranker  ) :
        picks = [[i] * 13 for i in range(11)]
        def RoundSlot(i) :
            return 13 - ranker( teamDict[i] )
        maxRounds = 5
        for team in teamList :
            teamPicks = getter( team )
            teamPicks.sort( key=lambda x:(x[0],RoundSlot(x[1])) )
            for (roundNum, section), pickNum in itertools.izip( teamPicks, itertools.count(0) ) :
                picks[roundNum-1][RoundSlot(section)] = (team.section, None, pickNum < team.emptySpots, None)
            numLeft = team.emptySpots - len(teamPicks)
            maxRounds = max(maxRounds, 5 + numLeft)
            for roundNum in range(5,11) :
                picks[roundNum][RoundSlot(team.section)] = (team.section, None, numLeft > 0, None)
                numLeft -= 1
        result = picks[:maxRounds]
        for roundNum, pickList in enumerate(result) :
            for pickNum, pick in enumerate(pickList) :
                if not isinstance(pick, tuple) :
                    Error( 'missing pick in round %d, pick #%d' % (roundNum, pickNum) )
        return result

    currYear = pool.PoolYear
    if not pool.Started :
        currYear -= 1
        if currYear not in years :
            years[currYear] = MakeDraftPickList( currYear, lambda x:x.picks, lambda x:x.lastyear )
    if pool.Started :
        years[currYear] = MakeDraftPickList( currYear, lambda x:x.picks, lambda x:x.officialRank )
        currYear += 1
        years[currYear] = MakeDraftPickList( currYear, lambda x:x.nextPicks, lambda x:x.officialRank )
    allYears = years.keys()
    allYears.sort()
    subsDict = {'allYears':allYears, 'teamDict':teamDict, 'teams':teamList, 'started':pool.Started}
    for year in allYears :
        subsDict['year'] = year
        subsDict['picks'] = years[year]
        try :
            template.DoTemplateSubstitution( 'draftinorder.html', 'draft/draft%d.html' % year, subsDict )
        except :
            print( year )
            print( years[year] )
            print( len(years[year]) )
            raise
    subsDict['year'] = pool.PoolYear
    template.DoTemplateSubstitution( 'draftbyteam.html', 'draftbyteam.html', subsDict )
    if pool.Started :
        perfList = []
        overall = 1
        for roundNum, roundPicks in zip( range(1,11), years[pool.PoolYear - 1] ) :
            for pickNum, pickInfo in zip( range(1,14), roundPicks ) :
                playerDict = pickInfo[3]
                if pickInfo[3] and pickInfo[3]['position'] != 'g' :
                    stats = None
                    if 'nhlname' in playerDict :
                        playerName = playerDict['nhlname']
                        stats, lastGame = SumStats( playerName, dailyData, datetime.date.min, datetime.date.max )
                    info = player.PlayerInfo( playerDict, stats )
                    perfList.append( (info, roundNum, pickNum, overall) )
                overall += 1
        perfList.sort( key=lambda x: (x[0].p, x[0].ppg, x[3]), reverse=True )
        subsDict['perfList'] = perfList
        template.DoTemplateSubstitution( 'draftperformance.html', 'draftperformance.html', subsDict )


def GenerateSite( dataDict, prevState, teamData, schedule, totalData, dailyData, prevDaily ) :
    Init()
    ReadAdjustDict()
    subsDict = {}
    gamesCounting = 0
    if pool.UsesSchedule :
        if pool.Started :
            gamesCounting, fracGames = util.CalcGamesCounting( schedule, util.TodaysDate ) 
        else :
            gamesCounting = 0
            fracGames = 0
        subsDict['gamesCounting'] = gamesCounting
        subsDict['fracGames'] = fracGames
    cap = 0
    if pool.UsesSalary :
        cap = 81500000 * 1.4
        subsDict['cap'] = util.Money(cap)
    teamList, smallPuck = MakeTeamList( teamData, dataDict, dailyData, prevState['totaldata'], schedule, cap, gamesCounting )
    teamDict = dict( (team.section, team) for team in teamList )
    MakeNewRosterPages( teamList )
    MakeRosterPages( teamList )
    newState = {'cap': cap, 'playerDict':dataDict}
    if pool.MultiYearPool :
        MakeTeamStatPages( teamList )
        MakeRankingPages( dataDict, teamDict, totalData, gamesCounting )
        MakeAllPlayersPage( dataDict, teamDict, totalData, dailyData, prevDaily )
        MakeDraftPages( teamList, teamDict, dataDict, dailyData )
        logList = logs.AddChangesToLog( newState, prevState, teamDict, Log )
        MakeLogPage( logList, teamList )
        newState['logList'] = logList
        subsDict['recentLogs'] = logs.GetRecentLogs(logList)
    elif pool.PoolName == 'Young Guns' :
        MakeYoungGunsPages( dataDict, teamDict, totalData )
    if smallPuck :
        smallPuck.gaa = round( smallPuck.gaa, 2 )
        subsDict['smallPuck'] = smallPuck
    subsDict.update( {'teams' : teamList, 'updated':util.TodaysDate, 'pool':pool.__dict__ , 'draftYear':pool.GetDraftYear()} )
    if pool.Started :
        teamList.sort( key=lambda x:x.points, reverse=True )
    else :
        teamList.sort( key=lambda x:x.poolpoints, reverse=True )
    template.DoTemplateSubstitution( 'frontpage.html', 'frontpage.html', subsDict )
    template.DoTemplateSubstitution( 'index.html', 'index.html', subsDict )
    Fini()
    util.ExecCommand( 'cp -r ../site/* site' )
    if os.path.exists( 'config/logos' ) :
        util.ExecCommand( 'cp -r config/logos/* site/logos' )
    if pool.MultiYearPool :
        util.ExecCommand( 'cp -r config/jerseys/* site/jerseys' )
    return newState
