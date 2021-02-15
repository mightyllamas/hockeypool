import copy
import util


def ParseTeamData( obj ) :
    pass
    

def GoaliePoints( x ) :
    return 1 * x.w + x.so

def ComputeScoring( teamList, dataDict, dailyData, *pos ) :
    elim = eval( open( 'config/eliminated.py', 'r').read() )
    elim = set( util.TeamNameFromAbbrev[x] for x in elim )
    for team in teamList :
        for pos, playerList in team.scoring.iteritems() :
            for player in playerList :
                if player.team in elim :
                    player.ghost = True
                    player.decoraters.append( 'X' )
            
        def CalcPoints( playerDict ) :
            totalPoints = 0
            for goalie in playerDict['g'] :
                goalie.pc = GoaliePoints( goalie )
            return sum( x.pc if pos =='g' else x.p for pos, playerList in playerDict.iteritems() for x in playerList )
        team.points = CalcPoints( team.scoring )
        team.prevPoints = CalcPoints( team.previous )
        team.deltaPoints = team.points - team.prevPoints
        team.CalcDeltaScoring()
        team.playersLeft = sum( 1 for playerList in team.scoring.itervalues() for player in playerList if not player.ghost )


def ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo ) :
    positions = [('s','Skaters'), ('g', util.PositionNameDict['g'])]
    rosters = ['main']
    baseGoalieStats = ['GP','dGP','PC','dPC','W','SO']
    goalieInfo = {'stats':baseGoalieStats, 'key':'W', 'dir':'desc' }
    positionInfo = { 's' : forwardInfo, 'g' : goalieInfo }

    def BoxpoolPlayoffGetRoster( team ) :
        skaters = team.scoring['lw'] + team.scoring['c'] + team.scoring['rw'] + team.scoring['d'] 
        skaters.sort( key=lambda x:x.p, reverse=True )
        goalies = copy.copy( team.scoring['g'] )
        goalies.sort( key=GoaliePoints, reverse=True )
        return {'s':skaters, 'g':goalies}
    return positions, positionInfo, rosters, BoxpoolPlayoffGetRoster

