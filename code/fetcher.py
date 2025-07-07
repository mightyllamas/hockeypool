import itertools
import json
import sys
import os
import urllib

import util
import pool

FetchLogName = 'log/fetch.log'

# http://www.nhl.com/stats/rest/skaters?isAggregate=false&reportType=basic&isGame=false&reportName=faceoffs&sort=[{%22property%22:%22faceoffsWon%22,%22direction%22:%22DESC%22}]&factCayenneExp=gamesPlayed%3E=1&cayenneExp=gameTypeId=2%20and%20seasonId%3E=20172018%20and%20seasonId%3C=20172018%20and%20teamId=53
# https://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&isGame=false&sort=%5B%7B%22property%22:%22wins%22,%22direction%22:%22DESC%22%7D,%7B%22property%22:%22savePct%22,%22direction%22:%22DESC%22%7D%5D&start=0&limit=50&factCayenneExp=gamesPlayed%3E=1&cayenneExp=gameTypeId=2%20and%20seasonId%3C=20192020%20and%20seasonId%3E=20192020

# https://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&isGame=false&sort=%5B%7B%22property%22:%22wins%22,%22direction%22:%22DESC%22%7D,%7B%22property%22:%22savePct%22,%22direction%22:%22DESC%22%7D,%7B%22property%22:%22playerId%22,%22direction%22:%22ASC%22%7D%5D&start=0&limit=100&factCayenneExp=gamesPlayed%3E=1&cayenneExp=gameTypeId=2%20and%20seasonId%3C=20212022%20and%20seasonId%3E=20212022

def FetchNHL( dirName ) :
	for team in util.ActiveTeamNames() :
		fName = '%s/nhl_%s.json' % (dirName, team[0])
		util.ExecCommand( "wget -O %s -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&reportType=basic&isGame=false&reportName=faceoffs&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=2%%20and%%20teamId=%s'" % (fName, FetchLogName, team[7]) )
	util.ExecCommand( "wget -O %s/nhl_goalies.json -a %s 'https://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&isGame=false&limit=100&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=2'" % (dirName, FetchLogName) )
	util.ExecCommand( "wget -O %s/nhl_goalies2.json -a %s 'https://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&isGame=false&start=100&limit=100&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=2'" % (dirName, FetchLogName) )

# http://www.nhl.com/stats/rest/skaters?isAggregate=false&reportType=basic&isGame=false&reportName=bios&sort=[{%22property%22:%22playerBirthDate%22,%22direction%22:%22DESC%22}]&factCayenneExp=gamesPlayed%3E=1&cayenneExp=gameTypeId=2%20and%20seasonId%3E=20172018%20and%20seasonId%3C=20172018%20and%20teamId=24
# http://www.nhl.com/stats/rest/goalies?isAggregate=false&reportType=goalie_basic&isGame=false&reportName=goaliebios&sort=[{%22property%22:%22playerBirthDate%22,%22direction%22:%22DESC%22}]&cayenneExp=gameTypeId=2%20and%20seasonId%3E=20172018%20and%20seasonId%3C=20172018

def FetchNHLBio( dirName ) :
	for team in util.ActiveTeamNames() :
		fName = '%s/bio_%s.json' % (dirName, team[0])
		util.ExecCommand( "wget -O %s -a %s 'http://api.nhle.com/stats/rest/en/skater/bios?isAggregate=false&isGame=false&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=2%%20and%%20teamId=%s'" % (fName, FetchLogName, team[7]) )
	util.ExecCommand( "wget -O %s/bio_goalies.json -a %s 'http://api.nhle.com/stats/rest/en/goalie/bios?isAggregate=false&isGame=false&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=2'" % (dirName, FetchLogName) )

# http://sports.yahoo.com/nhl/players/2102

def FetchYahooBio( linkList ) :
	dirName = 'fetch/yahoobio'
	util.Mkdir( dirName )
	count = 0
	for link in linkList :
		id = link.rsplit( '/', 1 )[1]
		fName = '%s/id%s.html' % (dirName, id)
		if not os.path.exists( fName ) :
			count += 1
			util.ExecCommand( 'wget -O %s -a %s %s' % (fName, FetchLogName, link), 5 )
			# make sure we don't annoy Yahoo
			if count >= 500 : break

# http://ca.sports.yahoo.com/nhl/teams/ana/stats/

def FetchYahoo( dirName ) :
	for entry in util.ActiveTeamNames() :
		abbrev = entry[0]
		fName = '%s/yahoo_%s.html' % (dirName, abbrev)
		util.ExecCommand( "wget -O %s -a %s 'http://ca.sports.yahoo.com/nhl/teams/%s/stats/'" % (fName, FetchLogName, abbrev), 5 )

# http://www.capfriendly.com/teams/jets/salary

def FetchCapFriendly( dirName ) :
	for entry in util.ActiveTeamNames() :
		fName = '%s/capfriendly_%s.html' % (dirName, entry[0])
		teamName = entry[2].lower().replace( ' ', '' )
		util.ExecCommand( "wget -O %s -a %s 'http://www.capfriendly.com/teams/%s/salary'" % (fName, FetchLogName, teamName), 5 )

def FetchPuckPedia( dirName ) :
	for entry in util.ActiveTeamNames() :
		fName = '%s/puckpedia_%s.html' % (dirName, entry[0])
		teamName = entry[1].lower().replace( ' ', '-' ).replace( '.', '' )
		util.ExecCommand( "wget -O %s -a %s 'http://www.puckpedia.com/team/%s'" % (fName, FetchLogName, teamName), 5 )

# did this fetch manually Y2016-18.   Can semi-automate next year hopefully!
# https://api-web.nhle.com/v1/schedule/2024-10-22

def FetchSchedule( dirName ) :
	currDate = '2024-10-18'
	while True :
		fileName = '%s/schedule_%s.json' % (dirName, currDate )
		util.ExecCommand( "wget -O %s -a %s 'https://api-web.nhle.com/v1/schedule/%s'" % (fileName, FetchLogName, currDate) )
		stuff = json.loads( util.ReadFile( fileName ) ) 
		if 'nextStartDate' not in stuff :
			break
		currDate = stuff['nextStartDate']
		print( currDate )


# http://www.nhl.com/stats/rest/skaters?isAggregate=false&reportType=basic&isGame=false&reportName=faceoffs&sort=[{%22property%22:%22faceoffsWon%22,%22direction%22:%22DESC%22}]&factCayenneExp=gamesPlayed%3E=1&cayenneExp=gameTypeId=3%20and%20seasonId%3E=20172018%20and%20seasonId%3C=20172018%20and%20teamId=53
# http://www.nhl.com/stats/rest/goalies?isAggregate=false&reportType=goalie_basic&isGame=false&reportName=goaliesummary&sort=[{%22property%22:%22wins%22,%22direction%22:%22DESC%22}]&cayenneExp=gameTypeId=3%20and%20seasonId%3E=20172018%20and%20seasonId%3C=20172018

def FetchPlayoffs( dirName ) :
	sortString = '%5B%7B"property":"playerId","direction":"ASC"%7D%5D'
	util.ExecCommand( "wget -O %s/skaters0.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=0&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/skaters1.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=100&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/skaters2.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=200&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/skaters3.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=300&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/skaters4.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=400&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/skaters5.json -a %s 'https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&start=500&limit=100&sort=%s&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName,sortString) )
	util.ExecCommand( "wget -O %s/goalies.json -a %s 'http://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&reportType=goalie_basic&isGame=false&reportName=goaliesummary&cayenneExp=seasonId=20242025%%20and%%20gameTypeId=3'" % (dirName, FetchLogName) )

# http://nhlnumbers.com/team-salaries/chicago-blackhawks-salary-cap/

def FetchNHLNumbers( dirName ) :
	for team in util.ActiveTeamNames() :
		name = team[1].replace(' ', '-').lower()
		name = name.replace('.', '')
		fName = '%s/nhlnumbers_%s.html' % (dirName, team[5])
		util.ExecCommand( "wget -O %s -a %s 'http://nhlnumbers.com/team-salaries/%d/%s-salary-cap'" % (fName, FetchLogName, pool.PoolYear, name) )

# http://capgeek.com/canucks/

def FetchCapGeek( dirName ) :
	for team in util.ActiveTeamNames() :
		team = team[2].lower().replace( ' ', '' )
		fName = '%s/capgeek_%s.html' % (dirName, team)
		util.ExecCommand( "wget -O %s -a %s 'http://capgeek.com/%s'" % (fName, FetchLogName, team) )

# http://sports.yahoo.com/nhl/injuries

def FetchInjuries( dirName ) :
	util.ExecCommand( "wget -O %s/injuries.html -a %s 'http://sports.yahoo.com/nhl/injuries'" % (dirName, FetchLogName) )


def InitFetch() :
	util.Mkdir( 'log' )
	util.ExecCommand( 'rm -f log/fetch.log' )
	util.ExecCommand( 'touch log/fetch.log' )


FetchFuncDict = {
	'nhl' : FetchNHL,
	'nhlbio' : FetchNHLBio,
	'yahoo' : FetchYahoo,
	'schedule' : FetchSchedule,
	'playoffs' : FetchPlayoffs,
	'nhlnumbers' : FetchNHLNumbers,
	'injuries' : FetchInjuries,
	'capgeek' : FetchCapGeek,
	'capfriendly' : FetchCapFriendly,
	'puckpedia' : FetchPuckPedia,
}

def FetchGroupedData( which ) :
	dirName = 'fetch/' + which
	util.Mkdir( dirName )
	FetchFuncDict[ which ]( dirName )
