import csv
import copy
import ConfigParser

import util
import template
import player

# this stuff ain't gonna work for any pool other than ifhl main.

def GetCSV( fileName, record ) :
    file = open( 'oldsite/' + fileName, 'r' )
    return csv.DictReader( file, fieldnames=record, restkey='leftover', doublequote=True, quotechar="'" )


def GetIFHLData() :
    teamIDs = set(str(x) for x in range(1,13))
    teamIDs.add( '25' )

    teamParser = ConfigParser.SafeConfigParser()
    teamParser.read( 'config/teams.ini' )
    newTeams = dict( (teamParser.get(sect,'name'),sect) for sect in teamParser.sections() )
    def MakeTeamDict( entry ) :
        name = entry['TeamName']
        teamDict = {'name':name, 'players':[]}
        if name in newTeams :
            teamDict['shortname'] = newTeams[name]
            if name == 'Frightning Dead Things' :
                teamDict['name'] = 'Frightning Dead'    # shorten it so it fits in the column
        elif name == 'Beachville Thrill' :
            teamDict['shortname'] = 'thrill'
            teamDict['name'] = teamParser.get('thrill','name')
        else :
            raise "can't find team named " + name
        return teamDict

    teamCSV = GetCSV('424.dat', ['TeamID', 'PoolID', 'TeamName']) 
    teamNames = dict( (x['TeamID'],MakeTeamDict(x)) for x in teamCSV if (x['TeamID'] in teamIDs) )

    allSeasons = dict( (str(x),copy.deepcopy(teamNames)) for x in range(1997,2009) if x != 2005 )
    teamStatsCSV = GetCSV( '425.dat', ["TeamID", "Season", "StatsDate", "Rank", "Players", "PlayersLW", "PlayersRW", "PlayersC", "PlayersD", "PlayersG", "Salary", "SalaryLW", "SalaryRW", "SalaryC", "SalaryD", "SalaryG", "Games", "GamesLW", "GamesRW", "GamesC", "GamesD", "GamesG", "Points"] )
    for teamStat in teamStatsCSV :
        teamID = teamStat['TeamID']
        season = teamStat['Season']
        if teamID in teamIDs and season in allSeasons :
            seasonData = allSeasons[season]
            teamData = seasonData[teamID]
            statsDate = teamStat['StatsDate']
            if 'statsDate' not in teamData or teamData['StatsDate'] < statsDate :
                teamData['statsdate'] = teamStat['StatsDate']
                teamData['points'] = float(teamStat['Points'])
                teamData['rank'] = teamStat['Rank']

    def MakePlayerDict( entry ) :
        dict = {'name': '%s %s' % (entry['NickName'],entry['LastName'])}
        id = entry['YahooId']
        if id != '0' :
            dict['link'] = 'http://sports.yahoo.com/nhl/players/' + id
        dict['playerid'] = entry['PlayerID']
        return dict

    playerCSV = GetCSV('420.dat',["PlayerID","LastName","NickName", "StatsName", "SalaryName", "ProfileName", "HistoryName", "Height", "Weight", "Birthdate", "DraftYear", "DraftRound", "DraftChoice", "IsRetired", "IsRookie", "Sweater", "ProfileWebPage", "HistoryWebPage", "YahooName", "YahooId"])
    playerInfo = dict( (x['PlayerID'],MakePlayerDict(x)) for x in playerCSV ) 
    playerSalaryCSV = GetCSV('422.dat', ["PlayerID", "Season", "LastStatsDate", "NHLTeamName", "Position", "PosChangeDate", "FirstTeamGame", "LastTeamGame", "Salary"] )
    playerSalaries = dict( ((x['PlayerID'],x['Season']),(int(x['Salary']),x['NHLTeamName'])) for x in playerSalaryCSV )

    playerStatsCSV = GetCSV( '427.dat', ["TeamID", "PlayerID", "Season", "StartDate", "EndDate", "Position", "G", "A", "P", "PIM", "PM", "GP", "MP", "GA", "PP", "SH", "GW", "GT", "Shots", "Percent", "GAA", "PPG", "LastG", "LastA", "LastP", "LastPIM", "LastPM", "LastGP", "LastMP", "LastGA", "LastPP", "LastSH", "LastGW", "LastGT", "LastShots", "LastPercent", "LastGAA", "LastPPG", "CountingGP", "CountingP", "LastCountingGP", "LastCountingP", "IsGhost"] )
    for playerStat in playerStatsCSV :
        teamID = playerStat['TeamID']
        season = playerStat['Season']
        if teamID in teamIDs and season in allSeasons :
            playerID = playerStat['PlayerID']
            playerEntry = copy.deepcopy(playerInfo[playerID])
            playerEntry['position'] = playerStat['Position'].lower()
            if playerEntry['position'] == '??' :
                playerEntry['position'] = 'c'           # what the heck?
            playerEntry['points'] = int(playerStat['P'])
            playerEntry['gamesplayed'] = int(playerStat['GP'])
            playerEntry['minutes'] = int(playerStat['MP'])
            playerEntry['shots'] = int(playerStat['Shots'])
            playerEntry['saves'] = playerEntry['shots'] - int(playerStat['GA'])
            playerEntry['gc'] = int(playerStat['CountingGP'])
            playerEntry['pc'] = float(playerStat['CountingP'])
            playerEntry['ghost'] = playerStat['IsGhost'] != '0'
            salaryEntry = playerSalaries.get( (playerID,season), None )
            if not salaryEntry :
                playerEntry['salary'] = 0
                playerEntry['team'] = 'Unknown'
            else :
                playerEntry['salary'] = salaryEntry[0]
                playerEntry['team'] = salaryEntry[1]
            allSeasons[season][teamID]['players'].append( playerEntry )

    return allSeasons


def WriteHistory() :
    ifhlData = GetIFHLData()
    forwardStats = ['GP','GC','P','PC','PPG','Salary']
    forwardInfo = {'stats':forwardStats, 'key':'PPG', 'dir':'desc'}
    positions = util.PositionNameDict.items()
    positionInfo = dict( (x[0],forwardInfo) for x in positions )
    goalieStats = ['GP','GC','P','GAA','Salary']
    positionInfo['g'] = {'stats':goalieStats, 'key':'GAA', 'dir':'asc'}
    subsDict = {'posInfo' : positionInfo,
                'positions' : positions,
                'rosterType' : 'history'}
    years = ifhlData.keys()
    years.sort()
    subsDict['years'] = years
    for year, seasonData in ifhlData.iteritems() :
        subsDict['year'] = year
        teams = [x for x in seasonData.itervalues() if 'points' in x]
        teams.sort( key=lambda x:x['points'], reverse=True )
        subsDict['teams'] = teams
        for team in teams :
            subsDict['team'] = team
            subsDict['teamname'] = '%s %s' % (team['name'], year)
            roster = util.MakeListByPosition()
            for member in team['players'] :
                roster[member['position']].append( player.PlayerInfo( member, member ) )
            for players in roster.itervalues() :
                players.sort( key=player.GetPlayerKey, reverse=True )
            subsDict['roster'] = roster
            template.DoTemplateSubstitution( 'rosterpage.html', 'history/%s_%s.html' % (team['shortname'], year), subsDict )

