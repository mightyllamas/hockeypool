import copy

import util
import pool
import player


def AllPlayoffRounds() :
    for round in range(1,pool.Round+1) :
        yield 'round%d' % round


class PlayoffRoundInfo :
    def __init__( self, prediction, games ) :
        self.prediction = prediction.strip().lower()
        self.ng = games
        self.p = 0

    def GetLinkName( self, decorateName, prefix, relative ) :
        return player.MakeTeamLinkName( util.TeamNameFromAbbrev[self.prediction], prefix )

    def GetStat( self, statName, prefix ) :
        if statName == 'Winner' :
            return player.MakeTeamLinkName( util.TeamNameFromAbbrev.get(self.winner,self.winner), prefix )
        return round( getattr( self, statName.lower() ), 2 )

    def GetSortName( self ) :
        return self.prediction


def ParseTeamData( team ) :
    team.rounds = {}
    for roundName in AllPlayoffRounds() :
        preds = (pred.split('-') for pred in getattr(team,roundName).split(','))
        team.rounds[roundName] = [PlayoffRoundInfo(pred[0],int(pred[1])) for pred in preds]


def ReadRoundInfo( fname ) :
    info = eval( open( fname,'r').read() )
    for round in AllPlayoffRounds() :
        resultList = info[round]
        newDict = dict( (x[0],x) for x in resultList )
        newDict.update( (x[2],x) for x in resultList )
        info[round] = newDict
    return info


def PickWinner( result ) :
    if result[1] == 4 :
        return result[0]
    elif result[3] == 4 :
        return result[2]
    return 'None'


def ComputeScoring( teamList, dataDict, dailyData, *pos ) :
    currRoundInfo = ReadRoundInfo( 'config/rounds.py' )
    prevRoundInfo = ReadRoundInfo( 'config/prevrounds.py' )
    out = set()
    for round in AllPlayoffRounds() :
        for home, homeWins, visit, visitWins in currRoundInfo[round].itervalues() :
            if visitWins == 4 :
                out.add( util.TeamNameFromAbbrev[home] )
            elif homeWins == 4 :
                out.add( util.TeamNameFromAbbrev[visit] )
    for team in teamList :
        for list in team.scoring.itervalues() :
            for player in list :
                if player.team in out :
                    player.ghost = True
        def CalcPoints( playerDict, roundInfo ) :
            def PlayerPoints( player ) :
                player.pc = player.p
                try :
                    if 'star' in player.extraOpts :
                        player.decoraters.append( 'S' )
                        player.pc = player.p * 2
                        return player.p * 2
                except :
                    pass
                return player.p
            pts = sum( PlayerPoints(x) for pos, playerList in playerDict.iteritems() for x in playerList if pos != 'g' )
            for player in playerDict['g'] :
                player.p = 2*player.w + player.so
                pts += PlayerPoints( player )
            for round in AllPlayoffRounds() :
                roundStats = roundInfo[round]
                roundPicks = team.rounds[round]
                for pred in roundPicks :
                    pred.dp = 0
                    pred.p = 0
                    pred.winner = 'None'
                    pred.gp = 0
                    if pred.prediction in roundStats :
                        result = roundStats[pred.prediction]
                        pred.winner = PickWinner( result )
                        pred.gp = result[1] + result[3]
                        if pred.winner == pred.prediction :
                            p = 5
                            if pred.ng == pred.gp :
                                p += 3
                            pred.dp = p - pred.p
                            pred.p = p
                    pts += pred.p
                roundPicks.sort( key=lambda x:x.p, reverse=True )
            return pts
        team.prevPoints = CalcPoints( team.previous, prevRoundInfo )
        team.points = CalcPoints( team.scoring, currRoundInfo )
        team.deltaPoints = team.points - team.prevPoints
        team.playersLeft = sum( 1 for list in team.scoring.itervalues() for player in list if not player.ghost )
        prevGoalies = dict( (x.name, x) for x in team.previous['g'] )
        for goalie in team.scoring['g'] :
            goalie.dpc = goalie.pc - prevGoalies[goalie.name].pc


def ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo ) :
    positions = [('f','Forward'), ('d',util.PositionNameDict['d']), ('g',util.PositionNameDict['g'])]
    for roundName in AllPlayoffRounds() :
        positions.append( (roundName, util.PlayoffRoundDict[roundName]) )
    rosters = ['main']
    baseForwardStats = ['GP','dGP','P','dP','PC','dPC','PPG','dPPG']
    forwardInfo = {'stats':baseForwardStats, 'key':'PC', 'dir':'desc' }
    positionInfo = dict( (x[0],forwardInfo) for x in positions )
    positionInfo['g'] = {'stats':['GP', 'dGP','P','dP','PC','dPC','W','SO'], 'key':'PC', 'dir':'desc' }
    for round in AllPlayoffRounds() :
        positionInfo[round] = {'stats':['NG', 'Winner','GP','P','dP'], 'key':'P', 'dir':'desc'}
    def NLGPlayoffGetRoster( team ) :
        team.scoring['g'].sort( key=lambda x:x.pc, reverse=True )
        team.scoring['d'].sort( key=lambda x:x.pc, reverse=True )
        forwards = team.scoring['lw'] + team.scoring['c'] + team.scoring['rw']
        forwards.sort( key=lambda x:x.pc, reverse=True )
        rosterDict = copy.copy( team.rounds )
        rosterDict.update( {'g':team.scoring['g'], 'd':team.scoring['d'], 'f':forwards} )
        return rosterDict
    return positions, positionInfo, rosters, NLGPlayoffGetRoster
