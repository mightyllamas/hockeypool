import datetime
import os
import re
import locale
import sys
import ConfigParser
import pool

# abbrev, fullname, suffix, panum, city, altabbrev, active, nhlnum, nhlabbrev
TeamNames = [
('njd', 'New Jersey Devils', 'Devils', 29, 'New Jersey','njd',True, 1, 'njd'),
('nyi', 'New York Islanders', 'Islanders', 31, 'NY Islanders','nyi',True,2, 'nyi'),
('nyr', 'New York Rangers', 'Rangers', 32, 'NY Rangers','nyr',True,3, 'nyr'),
('phi', 'Philadelphia Flyers', 'Flyers', 36, 'Philadelphia','phi',True,4, 'phi'),
('pit', 'Pittsburgh Penguins', 'Penguins', 39, 'Pittsburgh','pit',True,5, 'pit'),
('bos', 'Boston Bruins', 'Bruins', 4, 'Boston','bos',True,6, 'bos'),
('buf', 'Buffalo Sabres', 'Sabres', 6, 'Buffalo','buf',True,7, 'buf'),
('mon', 'Montreal Canadiens', 'Canadiens', 26, 'Montreal','mtl',True,8, 'mtl'),
('ott', 'Ottawa Senators', 'Senators', 34, 'Ottawa','ott',True,9, 'ott'),
('tor', 'Toronto Maple Leafs', 'Maple Leafs', 44, 'Toronto','tor',True,10, 'tor'),
('atl', 'Atlanta Thrashers', 'Thrashers', 2, 'Atlanta','atl',False,11,'atl'),
('car', 'Carolina Hurricanes', 'Hurricanes', 9, 'Carolina','car',True,12, 'car'),
('fla', 'Florida Panthers', 'Panthers', 18, 'Florida','fla',True,13, 'fla'),
('tam', 'Tampa Bay Lightning', 'Lightning', 43, 'Tampa Bay','tbl',True,14, 'tbl'),
('was', 'Washington Capitals', 'Capitals', 46, 'Washington','was',True,15, 'wsh'),
('chi', 'Chicago Blackhawks', 'Blackhawks', 10, 'Chicago','chi',True,16, 'chi'),
('cob', 'Columbus Blue Jackets', 'Blue Jackets', 13, 'Columbus','clb',True,29,'cbj'),
('det', 'Detroit Red Wings', 'Red Wings', 16, 'Detroit','det',True,17, 'det'),
('nas', 'Nashville Predators', 'Predators', 28, 'Nashville','nas',True,18, 'nsh'),
('stl', 'St. Louis Blues', 'Blues', 42, 'St Louis','stl',True,19, 'stl'),
('cgy', 'Calgary Flames', 'Flames', 7, 'Calgary','cgy',True,20, 'cgy'),
('col', 'Colorado Avalanche', 'Avalanche', 12, 'Colorado','col',True,21,'col'),
('edm', 'Edmonton Oilers', 'Oilers', 17, 'Edmonton','edm',True,22,'edm'),
('min', 'Minnesota Wild', 'Wild', 24, 'Minnesota','min',True,30,'min'),
('van', 'Vancouver Canucks', 'Canucks', 45, 'Vancouver','van',True,23,'van'),
('ana', 'Anaheim Ducks', 'Ducks', 1, 'Anaheim','ana',True,24,'ana'),
('dal', 'Dallas Stars', 'Stars', 14, 'Dallas','dal',True,25,'dal'),
('los', 'Los Angeles Kings', 'Kings', 22, 'Los Angeles','lak',True,26,'lak'),
#('pho', 'Phoenix Coyotes', 'Coyotes', 38, 'Arizona','phx',True,','phx'),
#('pho', 'Phoenix Coyotes', 'Coyotes', 38, 'Phoenix','phx',False,'phx'),
('ari', 'Arizona Coyotes', 'Coyotes', 38, 'Arizona','ari',False,53,'ari'),
('uta', 'Utah HC', 'Coyotes', 38, 'Utah','uta',True,59,'uta'),
('san', 'San Jose Sharks', 'Sharks', 41, 'San Jose','sjs',True,28,'sjs'),
('wpg', 'Winnipeg Jets', 'Jets', 1798, 'Winnipeg', 'wpg', True,52,'wpg'),
('vgk', 'Vegas Golden Knights', 'Golden Knights', 1799, 'Vegas', 'vgk', True, 54, 'vgk'),
('sea', 'Seattle Kraken', 'Kraken', 2112, 'Seattle', 'sea', True, 55, 'sea'),
]

NumNHLTeams = 32

def ActiveTeamNames() :
	return (x for x in TeamNames if x[6])

TeamAbbrevs = dict( (x[1],x[0]) for x in TeamNames )
TeamNameFromAbbrev = dict( (x[0],x[1]) for x in TeamNames )
TeamNameFromNHLNumbersAbbrev = dict( (x[5],x[1]) for x in TeamNames )
TeamSuffixFromAbbrev = dict( (x[0],x[2]) for x in TeamNames )
TeamNameFromLowerSuffix = dict( (x[2].lower().replace(' ',''), x[1]) for x in TeamNames )
TeamNameFromNHLAbbrev = dict( (x[8],x[1]) for x in TeamNames )
TeamAltSuffixFromAbbrev = dict( (x[0],x[5]) for x in TeamNames )
TeamNameFromNHLId = dict( (x[7],x[1]) for x in TeamNames )

PositionNameDict = {
	'lw':'Left Wing',
	'rw':'Right Wing',
	'c':'Centre',
	'd':'Defence',
	'g':'Goalie'
}

FunnyNames = { 'lw' : 'Larry', 'rw' : 'Ralph', 'c' : 'Charlie', 'd' : 'Doug' }


def TidyPosition( pos ) :
	pos = pos.lower()
	if pos == 'l' or pos == 'r' :
		return pos + 'w'
	return pos


PlayoffRoundDict = {
	'round1' : 'First Round',
	'round2' : 'Quarter Finals',
	'round3' : 'Semi Finals',
	'round4' : 'Stanley Cup'
}

def MakeListByPosition() :
	return dict( (x,[]) for x in PositionNameDict.iterkeys() )

StatsFields = ['points', 'gamesplayed', 'assists', 'goals', 'plusminus', 'faceoffs', 'faceoffsWon', 'wins', 'losses', 'shots', 'saves', 'minutes', 'shutouts']

TodaysDate = datetime.date.today()
YesterdaysDate = TodaysDate - datetime.timedelta(days=1)

def Init() :
	locale.setlocale(locale.LC_ALL,"")


def CalcGAA( shots, saves, minutes ) :
	return 0.0 if minutes == 0 else float(shots - saves) / minutes * 60

def CalcPPG( points, gp ) :
	if gp == 0 : return 0
	return float(points) / float(gp)

def CalcSavePercent( saves, shots ) :
	return 1 if shots == 0 else round( float(saves) / float(shots), 3 )
					

def Money( x ):
	return locale.currency( x, grouping=True )[:-3]

def Mkdir( dir ) :
	if not os.path.exists( dir ) :
		os.makedirs( dir )

digitStart = re.compile('[-0-9.]+$')
def IsNumeric( val ) :
	try :
		return re.match( digitStart, val )
	except: 
		print( val )
		raise

def ConvertTuple( x ) :
	if IsNumeric( x[1] ) :
		return (x[0], int(x[1]))
	elif x[0] == 'nhlposition' :
		return ('nhlPosition', x[1])
	return x


def ExecCommand( cmd, retry=0 ) :
	while True :
		retval = os.system( cmd )
		if retval :
			print 'Error executing %s' % (cmd)
			if retry == 0 :
				sys.exit(1)
			retry -= 1
		else:
			break


def AllOwnedPlayers() :
	teamParser = ConfigParser.SafeConfigParser()
	teamParser.read( 'config/teams.ini' )
	for section in teamParser.sections() :
		for playerName in open( 'config/teams/' + section, 'r') :
			opts = playerName.split( '+' )
			playerName = opts[0].lower().strip()
			if playerName:
				yield playerName 


def CalcGamesCounting( schedule, theDate ) :
	if not pool.Started: 
		return 0,0 
	if pool.Finished :
		return 82, 82
	totalGames = len(schedule)
	totalPlayed = sum( 1 for x in schedule if x[0] < theDate )
	fracGames = float(totalPlayed) / float(totalGames) * (totalGames * 2 / NumNHLTeams)
	return max(1,int(fracGames)), fracGames


def SeasonLength( schedule ) :
	if not pool.Started :
		return 82
	if pool.Finished :
		return 82
	return len(schedule) * 2 / NumNHLTeams


def ParseDate( x ) :
	parts = x.split('/')
	if len(parts) != 3 :
		Error( 'bad date found: ' + x )
	return datetime.date( int(parts[2]), int(parts[1]), int(parts[0]) )


def WillSwitchToWing( gp, faceoffs, paPosition, nhlPosition ) :
	return gp > 0 and (faceoffs / gp) < 5 and paPosition == 'c' and (nhlPosition == 'rw' or nhlPosition == 'lw')

def WillSwitchBack( gp, faceoffs, paPosition, nhlPosition ) :
	return gp > 0 and (faceoffs / gp) > 5 and paPosition == 'c' and (nhlPosition == 'rw' or nhlPosition == 'lw')


def PositiveNegative( key, printable ) :
	if key < 0 :
		printable = "<div class=\"negative\">%s</div>" % printable
	elif key > 0 :
		printable = "<div class=\"positive\">%s</div>" % printable
	return printable

def PosNeg( key ) :
	return PositiveNegative( key, str(key) )


def ReadFile( fName ) :
	file = open( fName, 'r' )
	data = file.read()
	file.close()
	return data

