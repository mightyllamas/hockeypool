
def ParseTeamData( obj ) :
    pass


def ComputeScoring( teamList, dataDict, dailyData, *pos ) :
    for team in teamList :
        def CalcPoints( playerDict ) :
            return sum( x.p for playerList in playerDict.itervalues() for x in playerList )
        team.points = CalcPoints( team.scoring )
        team.prevPoints = CalcPoints( team.previous )
        team.deltaPoints = team.points - team.prevPoints


def ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo ) :
    positions = [('s','Skaters')]
    rosters = ['main']
    positionInfo = dict( (x[0],forwardInfo) for x in positions )

    def IFHLPlayoffGetRoster( team ) :
        skaters = team.scoring['lw'] + team.scoring['c'] + team.scoring['rw'] + team.scoring['d'] + team.scoring['g']
        skaters.sort( key=lambda x:x.p, reverse=True )
        return {'s':skaters}
    return positions, positionInfo, rosters, IFHLPlayoffGetRoster

