import cPickle
import datetime
import os
import optparse
import pprint
import shutil
import sys

import util
import scraper
import fetcher
import joiner
import xmlwriter
import webwriter
import logs
import pool
import history
import team

SalarySource = 'capfriendly'


def MakePickleName( x, season=pool.PoolYear ) :
    return 'data/%d/%s.pickle' % (season, x)


def PickleData( data, name, season=pool.PoolYear ) :
    file = open( MakePickleName(name, season), 'w' )
    cPickle.dump( data, file )
    file.close()


def UnpickleData( name, season=pool.PoolYear ) :
    file = open( MakePickleName(name, season), 'r' )
    data = cPickle.load(file )
    file.close()
    return data


def StatsFileExists( name, season ) :
    return os.path.exists( MakePickleName( name, season ) )


def DailyMoves() :
    if not os.path.exists( 'backup' ) :
        print 'Error: no backup directory exists!'
        sys.exit(1)
    backFile = 'backup/daily%s.tgz' % datetime.date.today().isoformat()
    if os.path.exists( backFile ) :
        print 'Error: backup file %s already exists!' % backFile
        sys.exit(1)
    fetcher.InitFetch()
    statsDirs = 'fetch/' + pool.StatSource
    if pool.RegularSeason :
        statsDirs += ' fetch/%s' % (SalarySource) 
    util.ExecCommand( 'tar zcf %s data %s log' % (backFile, statsDirs) )
    shutil.copyfile( MakePickleName('poolstate', pool.PoolYear), MakePickleName('prevstate', pool.PoolYear) )


def NewSeason() :
    lastYear = pool.PoolYear - 1
    util.Mkdir( 'data/%d' % pool.PoolYear )
    if pool.MultiYearPool and StatsFileExists( 'poolstate', lastYear ) :
        prevdaily = UnpickleData( 'prevdaily', lastYear )
        dailyPrev = UnpickleData( 'dailydata', lastYear )
        prevdaily.append( (lastYear, dailyPrev) )
        PickleData( prevdaily, 'prevdaily' )
        poolstate = UnpickleData( 'poolstate', lastYear )
    else :
        poolstate = {}
    poolstate['dailydata'] = []
    poolstate['totaldata'] = {}
    if pool.UsesSalary :
        poolstate['startcap'] = poolstate['cap']
    PickleData( poolstate, 'prevstate', pool.PoolYear )
    util.Mkdir( 'backup' )


def StartSeason() :
    prevstate = UnpickleData( 'prevstate' )
    prevstate['startcap'] = prevstate['cap']
    prevstate['dailydata'] = []
    prevstate['totaldata'] = {}
    PickleData( prevstate, 'prevstate' )

def FetchData( args ) :
    for x in args :
        print 'Fetching ' + x
        fetcher.FetchGroupedData( x )


def LoadTeamData() :
    PickleData( team.LoadTeamDefinition(), 'teams' )


def ProcessHTML( args ) :
    for src in args :
        print 'Processing HTML for ' + src
        data = scraper.ScrapeData(src)
        PickleData( data, src )

def JoinData() :
    print 'Joining Data'
    statsYear = pool.GetStatsYear()
    statList = UnpickleData( pool.StatSource ) # , statsYear )
    totalData = joiner.WeldGameData( statList )
    prevState = UnpickleData( 'prevstate' )
    if pool.RegularSeason :
        nhlNumbers = UnpickleData( SalarySource )
        injuryData = UnpickleData( 'injuries', statsYear )
        nhlbio = UnpickleData( 'nhlbio', statsYear )
        joined = prevState['playerDict']
        joiner.MergeData( joined, totalData, nhlNumbers, injuryData, nhlbio )
    else :
        joined = joiner.NullJoin( statList )
    PickleData( joined, 'joined' )
    PickleData( totalData, 'totaldata' )
    PickleData( joiner.CalculateDailyData( prevState, totalData ), 'dailydata' )

def RenamePlayer( oldName, newName ) :
    def Rename( x ) :
        if oldName in x :
            x[newName] = x[oldName]
            del x[oldName]
    prevState = UnpickleData( 'prevstate' )
    Rename( prevState['totaldata'] )
    for date, theDict in prevState['dailydata'] :
        Rename( theDict ) 
    PickleData( prevState, 'prevstate' )

def FixContract( x ) :
    if util.IsNumeric(x) :
        val = float(x)
        if val < 100.0 :
            return str(val * 1000000)
        return x
    else :
        val = x.upper();
        if len(val) > 3 :
            val = val[:3]
    return  val
        

if 1 :
	def Patch() :
		prevState = UnpickleData( 'poolstate' )
		playerDict = prevState['playerDict']
		del playerDict['quintin hughes']
		PickleData( prevState, 'poolstate' )
if 0 :
    def Patch() :
        prevState = UnpickleData( 'prevstate' )
        newDaily = []
        dailyData = prevState['dailydata']
        for datetime, day in dailyData :
            newDay = {}
            for playerName, playerDict in day.items() :
                if 'saves' not in playerDict :
                    newDay[playerName] = playerDict
            newDaily.append( (datetime, newDay) )
        prevState['dailydata'] = newDaily
        PickleData( prevState, 'prevstate' )
    

def PrintRaw( args ) :
    printer = pprint.PrettyPrinter()
    for x in args :
        spl = x.split( '/' )
        if len(spl) == 1 :
            year = pool.PoolYear
        else :
            year = int(spl[0])
            x = spl[1]
        printer.pprint( UnpickleData( x, year ) )

def LoadRaw( args ) :  
    data = eval( open(args[1], 'r').read() )
    PickleData( data, args[0] )

def WriteXML( args ) :
    print 'Writing XML'
    for x in args :
        xmlwriter.WriteData( x, UnpickleData( x ) )

    
def WriteWeb() :
    print 'Generating web site'
    joinData = UnpickleData( 'joined' )
    prevState = UnpickleData( 'prevstate' )
    schedule = None
    if pool.UsesSchedule and pool.Started :
        schedule = UnpickleData( 'schedule' )
    else :
        schedule = None
    teamData = UnpickleData( 'teams' )
    totalData = UnpickleData( 'totaldata' )
    dailyData = UnpickleData( 'dailydata' )
    if StatsFileExists( 'prevdaily', pool.PoolYear ) :
        prevDaily = UnpickleData( 'prevdaily' )
    else :
        prevDaily = []

    stateDict = webwriter.GenerateSite( joinData, prevState, teamData, schedule, totalData, dailyData, prevDaily )
    stateDict['totaldata'] = totalData
    stateDict['dailydata'] = dailyData
    if pool.UsesSalary :
        stateDict['startcap'] = prevState['startcap']
    PickleData( stateDict, 'poolstate' )


def MailStatus() :
    logs.MailLogs( UnpickleData( 'poolstate' ) )


def FetchAndScrape( x ) :
    FetchData( x )
    ProcessHTML( x )


def StandardProcess() :
    FetchAndScrape( ['nhl', SalarySource, 'injuries'] )
    JoinData()
    WriteWeb()


def FullProcess() :
    StandardProcess()


def Main() :
    parser = optparse.OptionParser( version='0.1', description='Driver for the hockey pool stats collector' )
    parser.add_option( '-f', '--fetch', help="fetch files from websites", action='store_true' )
    parser.add_option( '-s', '--scrape', help="scrape data from fetched pages", action='store_true' )
    parser.add_option( '-j', '--join', help="join data together", action='store_true' )
    parser.add_option( '-p', '--print', help="print raw data", action='store_true', dest='doprint' )
    parser.add_option( '-x', '--xml', help="write xml data", action='store_true' )
    parser.add_option( '-w', '--web', help="generate web site", action='store_true' )
    parser.add_option( '-m', '--mail', help="mail status update", action='store_true' )
    parser.add_option( '--load', help="load data from text file", action='store_true', dest='doload' )
    parser.add_option( '--daily', help="do daily data preparation", action='store_true' )
    parser.add_option( '--newseason', help="prep for a new season ", action='store_true' )
    parser.add_option( '--startseason', help="starting a new season ", action='store_true' )
    parser.add_option( '--patch', help="custom fix the database ", action='store_true' )
    parser.add_option( '--history', help="generate history pages", action='store_true' )
    parser.add_option( '--team', help="load team info", action='store_true' )
    parser.add_option( '--std', help="standard stats processing", action='store_true' )
    parser.add_option( '--full', help="full stats processing", action='store_true' )
    if len(sys.argv) == 1 :
        parser.parse_args(args=['-h'])  # write help

    options, args = parser.parse_args()
    util.Init()

    if options.newseason : NewSeason()
    if options.startseason : StartSeason()
    if options.daily : DailyMoves()
    if options.team : LoadTeamData()
    if options.fetch : FetchData( args )
    if options.scrape : ProcessHTML( args )
    if options.std : StandardProcess()
    if options.full : FullProcess()
    if options.join : JoinData()
    if options.doprint : PrintRaw( args )
    if options.doload : LoadRaw( args )
    if options.xml : WriteXML( args )
    if options.web : WriteWeb()
    if options.mail : MailStatus()
    if options.patch : Patch()
    if options.history : history.WriteHistory()

Main()
