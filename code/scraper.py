import datetime
import glob
import json
import os
import re
import time
import unicodedata
import HTMLParser
import BeautifulSoup
import util
import pool
import pprint


def ReadFile( fName ) :
    file = open( fName, 'r' )
    data = file.read()
    file.close()
    return data

def UnParen( name ) :
    index = name.find( '(' )
    if index >= 0 :
        endIndex = name.find( ')' )
        if endIndex >= index :
            return name[:index - 1] + name[endIndex + 1:]
    return name

def GetStringChildren( soupObj ) :
    return ''.join( str(x) for x in soupObj.contents if not isinstance( x, BeautifulSoup.Tag ) ).strip()


# TODO: support points for goalies when they have them.
def ScrapeYahoo( fName ) :
    soup = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
    team = util.TeamNameFromAbbrev[fName[-8:-5]]         # fname should be "...yahoo_ana.html"
    playerDict = {}
    tables = soup.findAll( 'div', 'data-container' )
    if not tables :
        raise Exception( "unable to find data container in yahoo, file " + fName )
        return []
    try :
        for table in tables :
            if table.thead.tr.th.span.string == 'Skaters' :
                for player in table.tbody.findAll( 'tr' ) :
                    dataDict = {}
                    name = UnParen(player.th.a.string.strip())
                    dataDict['name'] = name
                    dataDict['nhlname'] = name.lower()
                    dataDict['team'] = team
                    dataDict['link'] = 'http://sports.yahoo.com' + player.th.a['href'].rstrip('/')
                    dataVals = player.findAll( 'td' )
                    dataDict['gamesplayed'] = int(dataVals[0].string)
                    dataDict['goals'] = int(dataVals[1].string)
                    dataDict['assists'] = int(dataVals[2].string)
                    dataDict['points'] = dataDict['goals'] + dataDict['assists']
                    dataDict['plusminus'] = int(dataVals[4].string)
                    if name not in playerDict :
                        playerDict[name] = dataDict
            else :
                for player in table.tbody.findAll( 'tr' ) :
                    dataDict = {}
                    name = UnParen(player.th.a.string.strip())
                    dataDict['name'] = name
                    dataDict['nhlname'] = name.lower()
                    dataDict['team'] = team
                    dataDict['link'] = 'http://sports.yahoo.com' + player.th.a['href'].rstrip('/')
                    dataVals = player.findAll( 'td' )
                    dataDict['gamesplayed'] = int(dataVals[0].string)
                    dataDict['minutes'] = int(dataVals[2].string)
                    dataDict['wins'] = int(dataVals[3].string)
                    dataDict['losses'] = int(dataVals[4].string)
                    dataDict['shots'] = int(dataVals[9].string)
                    dataDict['saves'] = int(dataVals[10].string)
                    dataDict['shutouts'] = int(dataVals[12].string)
                    dataDict['points'] = 0
                    playerDict[name] = dataDict
    except: 
        print( 'problem scraping ' + fName )
        raise
    if not playerDict :
        raise Exception( "no players found in yahoo scan" )
    return playerDict.values()


def ScrapePlayoffs( fName ) :
    return ScrapeNHL( fName )

def FixSpecialCharacters( name ) :
    x = name.replace( u'\xe9', u'e' )
    x = x.replace( u'\xe8', u'e' )
    x = x.replace( u'\xfc', u'u' )
    return x.replace( u'\xc9', u'E' )

def ScrapeSchedule( fName ) :
    stuff = json.loads( ReadFile( fName ) ) 
    schedList = []
    for date in stuff['dates'] :
        components = date['date'].split('-')
        currentDate = datetime.date( int(components[0]), int(components[1]), int(components[2]) )
        schedList.extend( (currentDate, FixSpecialCharacters(g['teams']['away']['team']['name']),FixSpecialCharacters(g['teams']['home']['team']['name'])) for g in date['games'] )
    schedList.sort()
    return schedList

class ParseMode :
    Active, Inactive, Retained = range(3)

def ScrapeCapFriendly( fName ) :
    soup = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
    lowerSuffix = fName.split('_')[1][:-5].lower()
    team = util.TeamNameFromAbbrev[lowerSuffix]
    allKids = soup.findAll( 'tr' )
    playerList = []
    retainedList = []
    inOthers = True
    mode = ParseMode.Active
    for record in allKids :
        recordClass = record.get( 'class', '' )
        if recordClass == '' or recordClass.startswith( 'stats' ) :
            continue
        entries = record.findAll( 'td' )
        if not entries :
            continue
        try :
            if len(entries[0]) == 1 :
                val = entries[0].string
            else :
                val = entries[0].contents[0].string
            if val :
                activePreludes = [
                    'FORWARDS', 'DEFENSE', 'GOALTENDERS',
                    'GOALIES', 'INJURED', 'LONG-TERM',
                    'SEASON OPENING', 'SUSPENDED', 'WAIVERS', 'TAXI SQUAD',
                    ]
                if any( val.startswith( x ) for x in activePreludes ) :
                    inOthers = False
                    mode = ParseMode.Active
                    continue
                if val.startswith( 'NON-ROSTER' ) :
                    inOthers = False
                    mode = ParseMode.Inactive
                    continue
                if val.startswith( 'RETAINED' ) :
                    inOthers = False
                    mode = ParseMode.Retained
                    continue
                inactivePreludes = [
                    'BUYOUT HISTORY', 'PROFESSIONAL TRYOUT', 'BURIED',
                    'SUBSTANCE ABUSE', 'RECAPTURE', 'TERMINATED', 'NHLPA PLAYER ASSISTANCE', 'REGISTRATION PENDING',
                    ]
                if any( val.startswith(x) for x in inactivePreludes ) :
                    inOthers = True
                    continue
                if val.lower().startswith( 'total' ) :
                    continue
            if not inOthers :
                dataDict = {}
                dataDict['capgeeklink'] = 'http://www.capfriendly.com' + entries[0].a['href'] 
                name = entries[0].a.string
                name = unicodedata.normalize('NFD', name)
                name = name.encode('ascii', 'ignore')
                name = name.replace( '&#39;', "'" )
                name = FixSpecialCharacters(name)
                if mode == ParseMode.Retained :
                    splitName = name.split( ' ' )
                    if len(splitName) != 2 :
                        raise Exception( "found an unexpected name format.  Want space separated. name %s, team %s".format(name,team)  )
                    splitName.reverse()
                else:
                    splitName = name.split( ','  )
                    if len(splitName) != 2 :
                        raise Exception( "found an unexpected name format.  Want comma separated. name %s, team %s".format(name,team)  )
                lastName, firstName = splitName
                if dataDict['capgeeklink'].endswith( 'aho1' ) :
                    lastName = 'Aho-D'
                elif dataDict['capgeeklink'].endswith( 'anderson1' ) :
                    lastName = 'Anderson-D'
                newName = firstName.strip() + ' ' + lastName.strip()
                dataDict['name'] = newName
                dataDict['keyname'] = dataDict['name'].lower()
                contract = []
                if mode != ParseMode.Retained  and len(entries[5]) > 0 :
                    dateStr = entries[6].span['title']
                    parsedDate = time.strptime( dateStr, '%b %d, %Y' )
                    dataDict['birthdate'] = datetime.date(parsedDate[0], parsedDate[1], parsedDate[2])
                rangeDelta = 4 if mode == ParseMode.Retained else 0
                for year in range(8 - rangeDelta,13 - rangeDelta) :
                    entry = entries[year]
                    entryLen = len(entry.contents)
                    if entryLen == 0 :
                        val = ''
                    elif entryLen == 1 :
                        div = entry.div
                        if len(div.contents) == 1 :
                            val = div.string
                            if val == None:
                                val = div.span.string
                        else :
                            val = div.find(text=True)
                    else :
                        what = entry.contents[0]
                        if len(what.contents) == 0 :
                            what = what.string
                        else :
                            what = what.contents[0].string
                        if what :
                            val = what.strip()
                            val = val.replace('$','')
                            val = val.replace(',','')
                        else :
                            val = ''
                    contract.append( val.encode('utf-8') )
                dataDict['contract'] = contract
                dataDict['team'] = team
                dataDict['active'] = mode == ParseMode.Active
                if mode == ParseMode.Retained :
                    retainedList.append( dataDict )
                else :
                    playerList.append( dataDict )
        except :
            print( fName )
            pprint.pprint( entries )
            raise
    if not playerList :
        raise Exception( "No players found in %s - check scraping code." % fName )
    return [(playerList, retainedList)]


def PostProcessCapFriendly( dataList ) :
    players = sum( (x[0] for x in dataList), [] )
    retained = sum( (x[1] for x in dataList), [] )
    playerLookup = dict( (p['name'],p) for p in players )
    for r in retained :
        if r['name'] not in playerLookup :
            print( 'retained player %s not found in player list' % (r['name']) )
        else :
            player = playerLookup[r['name']]
            contract = player['contract']
            for index, val in enumerate(r['contract']) :
                if util.IsNumeric( val ) :
                    contract[index] = str(int(contract[index]) + int(val))
    return players

def ScrapeNHLNumbers( fName ) :
    soup = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
    lowerSuffix = fName.split('_')[1][:-5].lower()
    team = util.TeamNameFromNHLNumbersAbbrev[lowerSuffix]
    allKids = soup.findAll( 'tr' )
    playerList = []
    inOthers = False
    inactive = False
    for record in allKids :
        entries = record.findAll( 'th' )
        if entries :
            inOthers = True
            val = entries[0].string
            if val :
                headerName = val.strip()
                if headerName.startswith('forwards') or headerName.startswith('defense') or headerName.startswith('goalie') :
                    inOthers = False
                    inactive = False
                elif headerName.startswith('inactive' ) :
                    inOthers = False
                    inactive = True
            continue
        entries = record.findAll( 'td' )
        if not entries :
            continue
        try :
            if inOthers :
                continue
            try :
                className = entries[0]['class']
            except KeyError :
                continue
            if className != 'fixed-side' :
                print( 'found a non-fixed-side element:' + className )
                continue
            dataDict = {}
            dataDict['capgeeklink'] = entries[0].a['href'] 
            name = entries[0].a.string
            name = name.replace( '&#39;', "'" )
            splitName = name.split( ',' )
            if len(splitName) == 1 :
                splitName = name.split(' ', 1)
            if splitName[1] == '(b. 1996) Aho' :
                splitName[1] = 'Aho-D'
            newName = splitName[0].strip() + ' ' + splitName[1].strip()
            newName = newName.strip()
            dataDict['name'] = newName
            dataDict['keyname'] = dataDict['name'].lower()
            contract = []
            for year in range(14,19) :
                val = entries[year].string
                if val == None :
                    val = entries[year].span.string
                    if val == None :
                        val = ''
                val = val.strip()
                val = val.replace('$','')
                val = val.replace(',','')
                if val == 'TBA' or val == '&nbsp;' :
                    val = ''
                val = val.upper()
                contract.append( val )
            dataDict['contract'] = contract
            dataDict['team'] = team
            dataDict['active'] = not inactive
            playerList.append( dataDict )
        except :
            print( fName )
            print( entries )
            raise
    if not playerList :
        raise Exception( "No players found in %s - check scraping code." % fName )
    return playerList


def ScrapeCapGeek( fName ) :
    lowerSuffix = fName.split('_')[1][:-5]
    team = util.TeamNameFromLowerSuffix[lowerSuffix]
    soup = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
    body = soup.find( 'tbody' )
    playerList = []
    skip = False
    for record in body.findAll( 'tr' ) :
        if record.get( 'class', '' ).startswith( 'total' ) :
            continue
        entries = record.findAll( 'td' )
        try :
            if entries[0].get( 'class', None ) == None :
                continue
            if entries[0]['class'] == 'section' :
                name = entries[0].span.strong.string
                skip = name.startswith( 'Buyouts' ) or name.startswith( 'Retained' ) or name.startswith( 'Carryover' )
            elif not skip :
                dataDict = {}
                if not entries[0].a or not entries[0].a.string:
                    continue
                last, first = entries[0].a.string.lower().split(',')
                first = first.split(None, 1 )[0]
                dataDict['name'] = first.strip() + ' ' + last.strip()
                dataDict['team'] = team
                dataDict['capgeeklink'] = 'http://capgeek.com' + entries[0].a['href']
                contract = []
                for year in range(2,10) :
                    elem = entries[year]
                    span = elem.find( 'span', 'salary' )
                    if not span :
                        span = elem.find( 'span', 'tracker_salary' )
                    if span :
                        if span.div :
                            salary = span.contents[1]
                        else :
                            salary = span.string
                        salary = salary.replace( '$', '' )
                        salary = salary.replace( ',', '' )
                        salary = str(float(salary) / 1000000)
                        contract.append( salary )
                    elif elem.div :
                        contract.append( elem.div.contents[0] )
                    else :
                        contract.append( '' )
                dataDict['contract'] = contract
                playerList.append( dataDict )
        except :
            print( fName )
            print( entries )
            raise
    return playerList


def ScrapeInjuries( fName ) :
    soup = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
    injuryList = []
    for tableRow in soup.findAll( 'tr', attrs={'class':re.compile('ysprow.*')} ) :
        dataVals = tableRow.fetch( 'td' )
        if len(dataVals) > 1 :
            try :
                dataDict = {}
                dataDict['name'] = dataVals[0].a.string.strip().lower()
                injuryDate = time.strptime( dataVals[1].string, '%b %d, %Y' )
                dataDict['date'] = datetime.date(injuryDate[0], injuryDate[1], injuryDate[2])
                reason = dataVals[3].string
                dataDict['details'] = "%s: %s" % (dataVals[2].string.strip(), reason.strip() if reason else '')
                injuryList.append( dataDict )
            except :
                print dataVals
                raise
    return injuryList
        

def ScrapeYahooBio( bioData, yahooData ) :
    inYahoo = set( x['link'].rsplit('/',1)[1] for x in yahooData )
    toGet = inYahoo.difference( x['id'] for x in bioData )
    for yahooId in toGet :
        fName = 'fetch/yahoobio/id%s.html' % yahooId
        soup  = BeautifulSoup.BeautifulSoup( ReadFile( fName ) )
        statsEntry = soup.find( 'ul', 'stats' )
        try : 
            if not statsEntry :
                statsEntry = soup.find( 'div', 'bio' )
                statsEntry = statsEntry.ul
            dataDict = {}
            dataDict['id'] = yahooId
            ageEntry = statsEntry.find( 'li', 'born' )
            timeEntry = ageEntry.find( 'time' )
            timeConv = '%b %d, %Y'
            if timeEntry :
                ageText = timeEntry.string.strip()
            elif ageEntry.dl :
                ageText = ageEntry.dl.dd.string
                timeConv = '%B %d, %Y'
            else :
                ageText = ageEntry.contents[1].split('-',1)[0].strip()
            birthDate = time.strptime( ageText, timeConv )
            dataDict['birthdate'] = datetime.date(birthDate[0], birthDate[1], birthDate[2])

            def GetValue( val ) :
                entry = statsEntry.find( 'li', val )
                if entry :
                    if entry.dl :
                        dataDict[val] = entry.dl.dd.string.encode('ascii','ignore')
                    else :
                        dataDict[val] = entry.contents[1].strip()
            GetValue( 'draft' )
            GetValue( 'height' )
            GetValue( 'weight' )
            GetValue( 'shoots' )
            bioData.append( dataDict )
        except :
            print fName
            print statsEntry
            raise
    return bioData

def KeyFix( k ) :
    k = str(k)
    if k in ['gamesPlayed', 'plusMinus'] :
        k = k.lower()
    elif k == 'shotsAgainst' :
        k = 'shots'
    elif k == 'playerName' :
        k = 'name'
    return k

def NHLNameFix( d ) :
    if 'skaterFullName' in d :
        d['name'] = d['skaterFullName']
    else :
        d['name'] = d['goalieFullName']
        d['positionCode'] = 'G'
    if d['name'] == 'Sebastian Aho' or d['name'] == 'Josh Anderson' :
        if d['positionCode'] == 'D' :
            d['name'] = d['name'] + '-D'
    d['name'] = FixSpecialCharacters( d['name'] )
    d['name'] = d['name'].encode()

def ScrapeNHL( fName ) :
    stuff = json.loads( ReadFile( fName ) ) 
    result = [dict((KeyFix(k),v) for k,v in x.iteritems()) for x in stuff['data']]
    for x in result :
        try : 
            NHLNameFix(x)
            x['nhlname'] = x['name'].lower()
            x['link'] = 'https://www.nhl.com/player/%s-%s' % (x['nhlname'].replace(' ', '-'), x['playerId'])
            if x['teamAbbrevs'] :
                team = x['teamAbbrevs'][-3:].lower()
                x['team'] = util.TeamNameFromNHLAbbrev[team]
            else :
                x['team'] = None
            pos = util.TidyPosition(x['positionCode'])
            if pos != 'f' :
                x['nhlPosition'] = pos
            if 'timeOnIce' in x :
                x['minutes'] = round(x['timeOnIce']/60)
            del x['seasonId']
        except :
            print( x )
            raise
    return result

def ScrapeNHLBio( fName ) :
    stuff = json.loads( ReadFile( fName ) ) 
    result = [dict((str(k),v) for k,v in x.iteritems()) for x in stuff['data']]
    for player in result :
        birthDate = [int(x) for x in player['playerBirthDate'].split('-')]
        player['birthdate'] = datetime.date(birthDate[0], birthDate[1], birthDate[2])
        for key in ['gamesPlayed', 'goals', 'points', 'seasonId', 'assists',
                    'playerFirstName','playerLastName','playerBirthDate',
                    'losses','otLosses','ties','wins'] :
            player.pop( key, None )
    return result

ScrapeFuncDict = {
    'yahoo' : ScrapeYahoo,
    'playoffs' : ScrapePlayoffs,
    'schedule' : ScrapeSchedule,
    'nhlnumbers' : ScrapeNHLNumbers,
    'injuries' : ScrapeInjuries,
    'capgeek' : ScrapeCapGeek,
    'capfriendly' : ScrapeCapFriendly,
    'nhl' : ScrapeNHL,
    'nhlbio' : ScrapeNHLBio,
}

def ScrapeData( source ) :
    util.Mkdir( 'data' )
    files = glob.glob( 'fetch/%s/*' % source )
    scrapeFunc = ScrapeFuncDict[source]
    dataList = []
    for filename in files :
        dataList = dataList + scrapeFunc( filename )
    if source == 'capfriendly' :
        dataList = PostProcessCapFriendly( dataList )
    return dataList
