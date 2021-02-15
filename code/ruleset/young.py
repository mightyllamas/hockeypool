import itertools
import pool
import util


def ParseTeamData( obj ) :
    pass


def ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo ) :
    positions = [('f','Forward'), ('d',util.PositionNameDict['d'])]
    rosters = ['main']
    baseForwardStats = ['GP','dGP','P','dP','PPG','dPPG','Age']
    forwardInfo = {'stats':baseForwardStats, 'key':'P', 'dir':'desc' }
    positionInfo = dict( (x[0],forwardInfo) for x in positions )
    def YoungGunsGetRoster( team ) :
        team.scoring['d'].sort( key=lambda x:x.p, reverse=True )
        forwards = team.scoring['lw'] + team.scoring['c'] + team.scoring['rw']
        forwards.sort( key=lambda x:x.p, reverse=True )
        return {'d':team.scoring['d'], 'f':forwards}
    return positions, positionInfo, rosters, YoungGunsGetRoster


def ComputeScoring ( teamList, dataDict, dailyData, prevTotal, schedule, cap, gamesCounting ) :
    for team in teamList :
        def CalcPosPoints( playerList, numPlayers ) :
            playerList.sort( key=lambda x:x.p )
            playerList = playerList[-numPlayers:]
            return sum( x.p for x in playerList )
        def CalcTeamPoints( roster ) :
            return CalcPosPoints( roster['lw'] + roster['c'] + roster['rw'], 3 ) +  CalcPosPoints( roster['d'], 2 )
        team.points = CalcTeamPoints( team.scoring )
        team.prevPoints = CalcTeamPoints( team.previous )
        team.predictedPoints = CalcTeamPoints( team.predicted )
        team.predictedToday = CalcTeamPoints( team.todayPrediction )
        team.deltaPoints = team.points - team.prevPoints
        team.predDeltaPoints = team.predictedToday - team.prevPoints
        team.poolpoints = team.points
