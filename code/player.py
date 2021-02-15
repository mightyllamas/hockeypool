import string
import util
import template
import pool

SafeTranslation = string.maketrans( "' .", "___" )


def MakePlayerFileName( playerName ) :
    return 'players/%s.html' % str(playerName).lower().translate( SafeTranslation )


def GetPlayerKey( x ) :
    if x.gp == 0 : return (0,0)
    if x.position == 'g' : return (1,-x.gaa)
    return (1,x.ppg)


def MakeTeamLinkName( teamName, prefix ) :
    if teamName not in util.TeamAbbrevs :
        teamLink = teamName
    else :
        teamLink = '<a href="http://sports.yahoo.com/nhl/teams/%s">%s</a>' % (util.TeamAbbrevs[teamName],teamName)
    return teamLink

class PlayerInfo :
    def __init__( self, player, stats, lastStats=None ) :
        try :
            self.name = player['name']
            self.status = player.get('status', 'Signed')
            self.position = player['position']
            self.salary = player.get( 'salary', pool.MinimumSalary )
            if self.salary < pool.MinimumSalary :
                self.salary = pool.MinimumSalary
            self.link = player.get( 'link', '' )
            self.salaryFancy = util.Money( self.salary )
            self.keyname = player.get('keyname', "unknown")
            self.nhlname = player.get('nhlname','')
            self.contract = player.get('contract',[])
            self.capgeeklink = player.get('capgeeklink','')
            self.extraOpts = player.get('extraOpts','')
            self.decoraters = []
            if 'team' in player :
                self.team = player['team']
                if pool.MultiYearPool :
                    contract = self.contract[0] if self.contract else ''
                    if contract.startswith( 'R' ) :
                        self.decoraters.append( 'RFA' )
                    elif contract.startswith( 'U' ) :
                        self.decoraters.append( 'UFA' )
                    elif self.status == 'Unsigned' :
                        self.decoraters.append( 'M' )
            else :
                self.team = 'Unsigned'
                self.decoraters.append( 'U' )
                
            self.injury = None
            if player.get( 'injury', None ) and pool.Started :
                injury = player['injury']
                self.injury = injury
                if injury['details'].startswith( 'Injured' ) :
                    dec = 'IR'
                else :
                    dec = 'DTD'
                self.decoraters.append( dec )
            if player.get('newposition','') :
                if player['newposition'] != player['position'] :
                    self.decoraters.append( player['newposition'].upper() )
            if 'birthdate' in player :
                delta = util.TodaysDate - player['birthdate']
                self.age = delta.days/365
            else :
                self.age = 0
            self.ifhlteam = player.get( 'ifhlteam', 'unsigned' )
            self.draft = ''
            if 'playerDraftYear' in player and player['playerDraftYear'] :
                self.draft = "%d Round %d, %d overall" % (player['playerDraftYear'],player['playerDraftRoundNo'], player['playerDraftOverallPickNo'])
            self.shoots = player.get( 'playerShootsCatches', '' )
            self.height = ''
            if player.get('playerHeight', None) :
                heightInInches = int(player.get('playerHeight'))
                self.height = '%d ft. %d in.' % ( heightInInches // 12, heightInInches % 12 )
            self.weight = player.get( 'playerWeight', '' )

            self.dgaa = 0
            if not stats :
                self.gp = 0
                self.p = 0
                self.ppg = 0
                self.gaa = 0
                self.faceoffs = 0
                self.savepercent = 0
                self.dgaa = 0
                self.shots = 0
                self.saves = 0
                self.minutes = 0
                self.w = 0
                self.so = 0
            else :
                self.p = stats.get('points', 0)
                self.gp = stats['gamesplayed']
                self.faceoffs = stats.get('faceoffs', 0)
                self.ppg = util.CalcPPG( self.p, self.gp )
                if player['position'] == 'g' :
                    self.shots = stats.get('shots', 0 )
                    self.saves = stats.get('saves', 0 )
                    self.minutes = stats['minutes']
                    self.w = stats.get( 'wins', 0 )
                    self.so = stats.get( 'shutouts', 0 )
                    if self.shots == 0 :
                        self.gaa = 0
                        self.savepercent = 0
                    else :
                        self.gaa = util.CalcGAA( self.shots, self.saves, self.minutes )
                        self.savepercent = util.CalcSavePercent( self.saves, self.shots )
                        if lastStats and self.minutes > lastStats['minutes']:
                            oldGaa = util.CalcGAA( self.shots - lastStats['shots'], self.saves - lastStats['saves'], self.minutes - lastStats['minutes'] )
                            self.dgaa = self.gaa - oldGaa
            if not lastStats :
                self.dgp = 0
                self.dp = 0
                self.dppg = 0
            else :
                self.dgp = lastStats['gamesplayed']
                self.dp = lastStats.get('points', 0)
                self.dppg = self.ppg - util.CalcPPG( self.p - self.dp, self.gp - self.dgp )
            self.gc = player.get('gc',0)
            self.dgc = 0
            self.pc = player.get('pc',0)
            self.dpc = 0
            self.roster = None
            self.ghost = player.get('ghost',False)
            self.isTotal = self.name.startswith( "Total" )
            self.dataFileName = MakePlayerFileName( self.name )
            self.fog = float(self.faceoffs) / self.gp if self.gp > 0 else 0
        except :
            print( 'problem creating player from %s' % repr(player) )
            raise


    def GetSortName( self ) :
        if self.isTotal :
            return "~"   # try to indicate it should sort last
        splitName = self.name.split(None,1)
        return '%s %s' % (splitName[1], splitName[0])


    def GetLinkName( self, decorateName, prefix, relative ) :
        linkName = self.name
        if self.decoraters != [] and decorateName  :
            linkName += ' (%s)' % ','.join( self.decoraters )
        if self.isTotal :
            return "<b>%s</b>" % linkName
        elif pool.RegularSeason :
            linkName = '<a href="%s%s%s">%s</a>' % (relative, prefix, self.dataFileName, linkName)
        else :
            linkName = '<a href="http://google.com/search?q=NHL+%s">%s</a>' % (self.name.replace(' ', '+'), linkName)
        if prefix == 'plain' :
            return linkName
        if self.ghost :
            linkName = '<div class="ghost">%s</div>' % linkName
        return linkName

    def GetYahooLinkName( self, prefix ) :
        linkName = self.name
        if self.ghost :
            linkName += ' (X)'
        if not self.link :
            return linkName
        linkName = '<a href="%s">%s</a>' % (self.link, linkName)
        if self.ghost and prefix != 'plain' :
            linkName = '<div class="ghost">%s</div>' % linkName
        return linkName


    def GetStat( self, statName, prefix ) :
        if statName == 'Sv%' :
            return self.savepercent
        elif statName == 'Salary' and prefix == 'plain' :
            return self.salaryFancy
        elif statName == 'Team' :
            return MakeTeamLinkName( self.team, prefix )
        elif statName[0] == '2':
            year = int(statName)
            if year == pool.PoolYear :
                if self.contract and (self.contract[0] == 'RFA' or self.contract[0] == 'UFA') :
                    return self.contract[0]
                return "%.3f" % (round(self.salary/1000000,3))
            offset = year - pool.PoolYear
            if offset >= len(self.contract) :
                return ''
            val = self.contract[offset]
            if util.IsNumeric(val) :
                return "%.3f" % (round(float(val)/1000000,3))
            return val
        return round( getattr( self, statName.replace('+','d').lower() ), 2 )

    def GetDecoratedStat( self, statName ) :
        if statName == 'Sv' :
            return "%.3f" % self.savepercent
        elif statName == 'Salary' :
            return self.salaryFancy
        elif statName == 'Team' :
            return MakeTeamLinkName( self.team, '' )
        elif statName[0] == '2':
            year = int(statName)
            if year == pool.PoolYear :
                if self.contract and (self.contract[0] == 'RFA' or self.contract[0] == 'UFA') :
                    return self.contract[0]
                return "%.3f" % (round(self.salary/1000000,3))
            offset = year - pool.PoolYear
            if offset >= len(self.contract) :
                return ''
            val = self.contract[offset]
            if util.IsNumeric(val) :
                return "%.3f" % (round(float(val)/1000000,3))
            return val
        return round( getattr( self, statName.replace('+','d').lower() ), 2 )
        value = getattr( self, statName.lower() )
        if any( statName.endswith( x ) for x in ('PPG', 'FOG', 'GAA') ) :
            printable = "%.2f" % value
        elif statName.endswith( 'PC' ) :
            printable = "%.1f" % value
        else :
            printable = str(value)
        if statName.startswith( 'd' ) :
            printable = util.PositiveNegative( -value if statName == 'dGAA' else value, printable )
        return printable
