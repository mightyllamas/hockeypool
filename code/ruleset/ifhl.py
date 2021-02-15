import itertools
import datetime

import pool
import util


def ParseTeamData( obj ) :
    def GetPicks( pickYear ) :
        picks = []
        for pickSpec in getattr( obj, 'picks%d' % pickYear ).split(',') :
            splitSpec = pickSpec.split('-')
            picks += zip([int(x) for x in splitSpec[1]],itertools.repeat(splitSpec[0]))
        return picks
    draftYear = pool.GetDraftYear()
    obj.picks = GetPicks( draftYear )
    obj.nextPicks = GetPicks( draftYear + 1 )


def GetGoalieAverages( teamList, dataDict, totalDict ) :
    for t in teamList :
        if not t.unofficial :
            for x in t.roster['g'] :
                if x.keyname in dataDict :
                    if 'nhlname' in dataDict[x.keyname] :
                        nhlname  = dataDict[x.keyname]['nhlname']
                        if nhlname in totalDict :
                            stats = totalDict[nhlname]
                            if stats['shots'] > 0 :
                                yield util.CalcGAA( stats['shots'], stats['saves'], stats['minutes'] )


def ComputeScoring ( teamList, dataDict, dailyData, prevTotal, schedule, cap, gamesCounting ) :
    smallpuck = max( (x for t in teamList if not t.unofficial for x in t.roster['g']), key=lambda x:x.gaa )
    if prevTotal :
        prevSmallpuckGAA = max( x for x in GetGoalieAverages( teamList, dataDict, prevTotal ) )
    else :
        prevSmallpuckGAA = smallpuck.gaa
    previousUpdate = datetime.date.min
    if len(dailyData) > 2 :
        previousUpdate = dailyData[-2][0]
    prevGamesCounting = util.CalcGamesCounting( schedule, previousUpdate )[0]
    for team in teamList :
        team.points, team.gamesMissing = team.ComputePoints( team.scoring, gamesCounting, smallpuck.gaa )
        team.prevPoints, prevGamesMissing = team.ComputePoints( team.previous, prevGamesCounting, prevSmallpuckGAA )
        team.predictedPoints, predGamesMissing = team.ComputePoints( team.predicted, util.SeasonLength(schedule), smallpuck.gaa )
        team.predictedToday, x = team.ComputePoints( team.todayPrediction, gamesCounting, smallpuck.gaa )
        team.FinishStats( gamesCounting )
        team.AddGhosts( team.gamesMissing, smallpuck, prevGamesMissing, prevSmallpuckGAA )
        team.CalcDeltaScoring()
        team.AddTotals()
        team.remain = cap - team.salary
        team.remainFancy = util.Money( team.remain )
        if pool.Started :
            team.deltaPoints = team.points - team.prevPoints
            team.predDeltaPoints = team.predictedToday - team.prevPoints
        else :
            team.deltaPoints = 0
            team.predDeltaPoints = 0
        team.alert = ''.join( pos[0].upper() for pos,num in team.gamesMissing.iteritems() if num > 0 )
        if team.remain < 0 :
            team.alert += 'S'
            if hasattr( team, 'salarydate' ) :
                start = util.ParseDate( team.salarydate )
                team.alert += '(%d)' % (14 - (datetime.date.today() - start).days)
    return smallpuck


def ConfigureRoster( baseForwardStats, baseGoalieStats, forwardInfo ) :
    mainStats = ['salary','age']
    positions = util.PositionNameDict.items()
    rosters = ['main', 'score','wide','predicted','salary','trading','extra']
    forwardInfo['stats'] = forwardInfo['stats'] + mainStats
    positionInfo = dict( (x[0],forwardInfo) for x in positions )
    positionInfo['g'] = {'stats':baseGoalieStats + mainStats, 'key':'GAA', 'dir':'asc' }
    rosterFn = lambda x:x.roster
    return positions, positionInfo, rosters, rosterFn
