import copy
import sys
import os

import util
import pool
import ConfigParser


def CommaSeparatedFile( fileName ) :
	for line in open( fileName, 'r' ) :
		a = line.split(',', 1 )
		yield ( a[0].strip(), a[1].strip() )


def AddDict( a, b, theDict ) :
	if a not in theDict :
		theDict[a] = [b]
	else :
		theDict[a].append(b)


def ReadNameDict( fileName ) :
	nameDict = {}
	for first, second in CommaSeparatedFile( fileName ) :
		AddDict( first, second, nameDict )
		AddDict( second, first, nameDict )
	return nameDict


def WeldGameData( dataList ) :
	nhlDict = {}
	for curr in dataList:
		nhlName = curr['nhlname']
		if nhlName in nhlDict :
			existing = nhlDict[nhlName]
			for field in util.StatsFields :
				if field in existing :
					existing[field] += curr[field]
		else :
			nhlDict[nhlName] = curr
	return nhlDict


LogFile = None
def WriteLogFile( x ) :
	global LogFile
	if not LogFile :
		LogFile = open( 'log/join.log', 'w' )
	try :
		LogFile.write( x + '\n' )
	except :
		print( x )
		raise


class NameMatcher :
	def __init__( self ) :
		self.firstNames = ReadNameDict( 'config/first_names' )
		self.lastNames = ReadNameDict( 'config/last_names' )
		self.specialNames = dict( CommaSeparatedFile( 'config/name_map' ) )

	def FindMatchingName( self, keyname, currDict ) :
		if keyname in currDict :
			return keyname
		if keyname in self.specialNames :
			match = self.specialNames[keyname]
			if match not in currDict :
				WriteLogFile( 'special match %s to %s not found in nhl dict!' % (keyname, match ) )
			else :
				return match
		nameSplit = keyname.split(None,1)
		def PossibleNames( name, possibles ) :
			return [name] + possibles.get(name,[])
		possibleLast = PossibleNames( nameSplit[1], self.lastNames )
		possibleFirst = PossibleNames( nameSplit[0], self.firstNames )
		possibleFirst.append( nameSplit[0][0] + '.' )
		for first in possibleFirst :
			for last in possibleLast :
				match = first + ' ' + last
				if match in currDict :
					 return match
		return None


TheNameMatcher = None
def GetNameMatcher() :
	global TheNameMatcher
	if not TheNameMatcher :
		TheNameMatcher = NameMatcher()
	return TheNameMatcher


class ExtraDataMerger :
	def __init__( self, injuryData, nameMatcher, nhlbio ) :
		self.injuryData = dict( (x['name'],x) for x in injuryData )
		self.matcher = nameMatcher
		self.nhlbio = dict( (x['playerName'].lower(), x) for x in nhlbio )

	def Merge( self, player ) :
		try : 
			keyname = player['keyname']
			name = player.get('nhlname', keyname)
			if name in self.injuryData :
				player['injury'] = self.injuryData[name]
			if name in self.nhlbio :
				player.update( self.nhlbio[name] )
		except :
			print( "Error merging player data" )
			print( player )
			raise

def AddFakeKeyStats( newDict ) :
	try :
		newDict['keyname'] = newDict['nhlname']
		newDict['status'] = 'Unsigned'
		newDict['position'] = newDict['nhlPosition']
	except :
		print( newDict )
		raise
	return newDict


def MakeNullJoinDict( oldDict ) :
	newDict = dict( (x, oldDict[x]) for x in ['name','nhlname','link','team'] )
	return AddFakeKeyStats( newDict )


def NullJoin( dataList ) :
	result = dict( (x['nhlname'],AddFakeKeyStats(x)) for x in dataList )
	if os.path.exists( 'config/players.ini' ) :
		playerParser = ConfigParser.SafeConfigParser()
		playerParser.read( 'config/players.ini' )
		for sect in playerParser.sections() :
			result[sect] = dict(util.ConvertTuple(x) for x in playerParser.items(sect))
	return result


def AddPlayerEntry( matcher, playerDict, keyname, player ) :
	match = matcher.FindMatchingName( keyname, playerDict )
	if match :
		playerDict[match].update( player )
		return playerDict[match]
	WriteLogFile( 'player %s added to DB' % keyname )
	if 'status' not in player :
		player['status'] = 'Signed'
	if 'salary' not in player :
		player['salary'] = pool.MinimumSalary
	if 'active' not in player :
		player['active'] = True
	playerDict[keyname] = player
	return player

# Note: this modifies the contents of playerDict
def MergeData( playerDict, statsDict, nhlNumbers, injuryData, nhlbio ) :
	statsDict = copy.copy( statsDict )
	matcher = GetNameMatcher()
	dataMerger = ExtraDataMerger( injuryData, matcher, nhlbio )
	for player in playerDict.itervalues() :
		player['active'] = False
		player['ifhlteam'] = 'unsigned'		# FIXME: this is so hacky - remove it later!
		player['injury'] = None
		player['newposition'] = ''
		player['status'] = 'Unsigned'

	if os.path.exists( 'config/players.ini' ) :
		playerParser = ConfigParser.SafeConfigParser()
		playerParser.read( 'config/players.ini' )
		for sect in playerParser.sections() :
			AddPlayerEntry( matcher, playerDict, sect, dict(util.ConvertTuple(x) for x in playerParser.items(sect)) )
	
	for player in nhlNumbers :
		dictEntry = None
		keyname = player['keyname']
		if util.IsNumeric(player['contract'][0]) :
			player['salary'] = float(player['contract'][0])
			player['status'] = 'Signed'
		else :
			player['status'] = 'Unsigned'
		match = matcher.FindMatchingName( keyname, statsDict )
		if match :
			dictEntry = statsDict.pop( match )
			link = dictEntry['link']
			player['link'] = link
			player['nhlname'] = dictEntry['nhlname']
			if 'nhlPosition' in dictEntry :
				player['nhlPosition'] = util.TidyPosition(dictEntry.get('nhlPosition'))
		dataMerger.Merge( player )
		AddPlayerEntry( matcher, playerDict, keyname, player )

	# check for NHL players that weren't in NHLNumbers
	for name, subDict in statsDict.iteritems() :
		WriteLogFile( 'unable to find NHL player %s in NHLNumbers' % name )
		player = AddFakeKeyStats( subDict )
		dataMerger.Merge( player )
		player = AddPlayerEntry( matcher, playerDict, name, player )
		# fix contract
		if 'contract' in player :
			contract = player['contract']
			while util.IsNumeric(contract[0]) :
				contract = contract[1:] + ['']
			player['contract'] = contract
	
	# now go through and figure out what the player position should actually be
	for name, player in playerDict.iteritems() :
		position = player.get('nhlPosition', None)
		if not pool.FixPositions :
			player['position'] = position
		else :
			if not player.get('position',None) :
				player['position'] = position
			elif position != player['position'] :
				player['newposition'] = position

def CalculateDailyData( prevState, totalData ) :
	oldTotal = prevState['totaldata']
	dailyData = prevState['dailydata']
	entries = {}
	def UpdateStats( oldStats, data, name ) :
		if any( oldStats[x] != data[x] for x in util.StatsFields if x in data and x in oldStats ) :
			negativeData = False
			entries[name] = dict( (x, data[x] - oldStats[x]) for x in util.StatsFields if x in data and x in oldStats )
			if entries[name]['gamesplayed'] < -1 :
				negativeData = True
				print 'negative games played - somebody is feeding bad data!  player name %s' % name
			if negativeData :
				entries[name] = dict( (x, data[x]) for x in util.StatsFields if x in data )

	for name, data in totalData.iteritems() :
		if name not in oldTotal :
			if	data['gamesplayed'] > 3 and pool.Started : # and name != 'gustav nyquist' and name != 'eetu luostarinen' :
				WriteLogFile( 'data anomaly for %s.  Checking if NHL changed the name' % name )
				matchedName = GetNameMatcher().FindMatchingName( name, oldTotal )
				if not matchedName :
					if  name.endswith('greer') : # or name.endswith('girard') : #or name == 'mike smith' or name == 'stuart skinner' or name.endswith('koskinen') or name == 'andrew hammond' or name == 'tuukka rask' or name.endswith('berube') :
						print( "slamming in " + name )
						if 1 :
							entries[name] = dict( (x, data[x]) for x in util.StatsFields if x in data )
						else :
							totalStats = dict( (x,0) for x in util.StatsFields )
							for day, stats in dailyData :
								if name in stats :
									currDay = stats[name]
									for x in util.StatsFields :
									   if x in currDay :
											totalStats[x] += currDay[x]
							UpdateStats( totalStats, data, name )
						continue
					print data
					print 'daily games anomaly for %s - please investigate' % name
					sys.exit(1)
				else :
					WriteLogFile( 'data source changed name from %s to %s' % (matchedName, name) )
				for day, stats in dailyData :
					if matchedName in stats :
						playerStats = stats[matchedName]
						del stats[matchedName]
						stats[name] = playerStats
				UpdateStats( oldTotal[matchedName], data, name )
			else :
				entries[name] = dict( (x, data[x]) for x in util.StatsFields if x in data )
		else :
			UpdateStats( oldTotal[name], data, name )
	if entries :
		dailyData.append( (util.TodaysDate, entries)  )
	return dailyData
