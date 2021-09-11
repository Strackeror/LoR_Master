from Models import riot
import Models.utility as utility
import constants as cs
from Models.leaderboard import getRankStr, checkRank
import Models.network

class DeckDetail:
    def __init__(self, matches: int , winNum: int, time: str):
        self.matches = matches
        self.winNum = winNum
        self.time = time
        self.history = ''

class OpponentFlask:
    def __init__(self):
        self.history = []

class Player:
    def __init__(self, riot):
        self.sortedDecksCode = []
        self.riot = riot
        self.summary = {}
        self.matchesJson = []
        self.historyFlask = OpponentFlask()

    def addMatchToSummary(self, code, outcome, time):
        if code in self.summary:
            self.summary[code].matches += 1
            if outcome == 'win':
                self.summary[code].winNum += 1
        else:
            winNum = 0
            if outcome == 'win':
                winNum = 1
            self.summary[code] = DeckDetail(1, winNum, time)

        for key in self.summary:
            if key != code:
                self.summary[key].history += 'E'
            else:
                if outcome == 'win':
                    self.summary[key].history += 'W'
                else:
                    self.summary[key].history += 'L'

        matchNum = len(self.summary[list(self.summary.keys())[0]].history)

        for key in self.summary:
            fill = 'E' * (matchNum - len(self.summary[key].history))
            self.summary[key].history = fill + self.summary[key].history

    def checkOpponent(self, name, tag, showMessage, showMatchs, showDecks):
        puuid = self.riot.getPlayerPUUID(name, tag)
        if puuid is None:
            print("无法获取对手puuid")
            return
        matchIds = self.riot.getMatches(puuid, False)
        if matchIds is None:
            print("无法获取对手最近对战记录")
            return
        else:
            if len(matchIds) > cs.MAX_NUM_TRACK:
                matchIds = matchIds[0:cs.MAX_NUM_TRACK]
        deckCodes = []
        loop = self.riot.asyncio.new_event_loop()
        self.riot.asyncio.set_event_loop(loop)
        tasks = [self.riot.aioMatchDetail(id) for id in matchIds]
        details = loop.run_until_complete(self.riot.asyncio.gather(*tasks))

        self.summary = {}
        for detail in details:
            if str(detail).isdigit():
                print('Retry after ' + str(detail) + ', Riot server is busy.')
                showMessage('Riot server [' + Models.network.API_KEY[-4:] + '] busy ' +
                            str(detail))
                continue
            if detail is None:
                continue
            else:
                if detail['info']['game_type'] != 'Ranked':
                    print(detail['info']['game_type'])
                    continue
            riotId = detail['metadata']['participants']
            for count, riotId in enumerate(riotId):
                if riotId == puuid:
                    myDetails = detail['info']['players'][count]
                    deckCodes.append(myDetails['deck_code'])
                    startTime = detail['info']['game_start_time_utc']
                    outcome = myDetails["game_outcome"]
                    self.addMatchToSummary(
                        myDetails['deck_code'], outcome,
                        utility.toLocalTimeString(startTime, True))
                    showMatchs(utility.toLocalTimeString(startTime, True),
                               utility.getFactionString(myDetails["factions"]),
                               myDetails['deck_code'], outcome)
        showDecks(self.getNoDuplicate(deckCodes), len(deckCodes))

    def getNoDuplicate(self, deckCodes):
        deckslist = dict(
            zip(list(deckCodes),
                [list(deckCodes).count(i) for i in list(deckCodes)]))
        deckslist = dict(
            sorted(deckslist.items(), key=lambda item: item[1], reverse=True))
        # to-do
        self.sortedDecksCode = sorted(deckslist,
                                      key=deckslist.get,
                                      reverse=True)
        return deckslist

    def inspectPlayer(self, name, tag, showlog, showSummary, finishTrigger):
        puuid = self.riot.getPlayerPUUID(name, tag)
        if puuid is None:
            print(
                '', name + '#' + tag + ' does not exist. Please check player name and player tag')
            return finishTrigger(
                '', name + '#' + tag + ' does not exist. Please check player name and player tag')
        matchIds = self.riot.getMatches(puuid)
        winNum = 0
        matchNum = 0
        if matchIds is None:
            print(name + '#' + tag,
                  ' has no recent match records')
            return finishTrigger(name + '#' + tag,
                                 ' has no recent match records')
        deckCodes = []
        self.summary = {}
        matchNum, winNum = self.readMatchIds(
            matchIds, matchNum, finishTrigger, name, tag, puuid, deckCodes, showlog, winNum)

        if matchNum != 0:
            print(
                str(winNum) + ' wins' + ' out of ' + str(matchNum) +
                ' rank matchs')
            print("Win rate:", str(int(winNum / matchNum * 100)) + "%")
            showSummary(self.getNoDuplicate(deckCodes))
            return finishTrigger(
                name + '#' + tag, ' Win rate: ' +
                str(int(winNum / matchNum * 100)) + "%  " + str(winNum) +
                ' wins' + ' out of ' + str(matchNum) + ' matches')
        else:
            print(name + '#' + tag,
                  ' has no recent rank match records')
            return finishTrigger(name + '#' + tag,
                                 ' has no recent rank match records')

    def readMatchIds(self, matchIds, matchNum, finishTrigger, name, tag, puuid, deckCodes, showlog, winNum):
        for matchId in matchIds:
            try:
                # If match number bigger than MAX, getDetail will only ruturn data from cache
                detail = self.riot.getDetail(matchId, matchNum)
                if str(detail).isdigit():
                    finishTrigger(
                        name + '#' + tag, 'Riot server [' + Models.network.API_KEY[-4:] + '] busy ' +
                        str(detail))
                    continue
                if detail is None:
                    continue
                print('detail', detail)
                gameMode = detail['info']['game_mode']
                gameType = detail['info']['game_type']
                startTime = detail['info']['game_start_time_utc']

                if gameMode in cs.UNSUPPORTED_MODE:
                    continue
                
                if gameType in cs.UNSUPPORTED_TYPE:
                    continue

                matchNum += 1
                riotId = detail['metadata']['participants']
                outcome = None
                opponentDetail = None
                myDetails = None
                totalTurn = detail['info']['total_turn_count']
                myIndex = 1
                opponentIndex = 0
                if riotId[0] == puuid:
                    myIndex = 0
                    opponentIndex = 1
                else:
                    # differnet APIs has df puuid, has to double check if equal playernames when may using caching data
                    indexName = self.riot.getPlayerName(riotId[0])
                    if indexName[0].lower() == name.lower() and indexName[1].lower() == tag.lower():
                        myIndex = 0
                        opponentIndex = 1
                opName = self.riot.getPlayerName(riotId[opponentIndex])
                fullName = opName[0] + '#' + opName[1]
                opponentDetail = detail['info']['players'][opponentIndex]
                myDetails = detail['info']['players'][myIndex]
                outcome = myDetails["game_outcome"]
                if outcome == 'win':
                    winNum += 1
                print(detail)
                self.addMatchToSummary(
                    myDetails['deck_code'], outcome, utility.toLocalTimeString(startTime, True))
                deckCodes.append(myDetails['deck_code'])
                settingServer = self.riot.network.setting.getServer()
                rank = getRankStr(opName[0], settingServer)
                gameTypeString = '[' + gameType + ']'
                if gameType == '':
                    gameTypeString = ''
                showlog(fullName + ' ' + rank,
                        gameTypeString + ' [' + gameMode + '] ' +
                        utility.toLocalTimeString(startTime), outcome,
                        myDetails['deck_code'],
                        utility.getFactionString(myDetails["factions"]),
                        opponentDetail['deck_code'],
                        utility.getFactionString(opponentDetail["factions"]),
                        str(totalTurn) + ' Order of Play: ' + str(myDetails['order_of_play']), matchNum)
            except Exception as e:
                print('Read MatchId Error match id: ', matchId , e)
                continue
        return matchNum, winNum

    def loadMatchsToFlask(self):
        self.historyFlask.history = []
        for deckCode in self.summary:
            match = {}
            match['time'] = self.summary[deckCode].time
            match['deckCode'] = deckCode
            match['matches'] = self.summary[deckCode].matches
            match['winrate'] = self.summary[
                deckCode].winNum / self.summary[deckCode].matches
            match['history'] = self.summary[deckCode].history
            self.historyFlask.history.append(match)

    def inspectFlask(self, name, tag):
        self.matchesJson = []
        puuid = self.riot.getPlayerPUUID(name, tag)
        if puuid is None:
            print(
                '', name + '#' + tag + ' does not exist. Please check player name and player tag')
            return
        matchIds = self.riot.getMatches(puuid)
        winNum = 0
        matchNum = 0
        if matchIds is None:
            print(name + '#' + tag,
                  ' has no recent match records')
            return
        deckCodes = []
        self.summary = {}
        matchNum, winNum = self.processMatchIds(
            matchIds, matchNum, name, tag, puuid, deckCodes, winNum)

        if matchNum != 0:
            print(
                str(winNum) + ' wins' + ' out of ' + str(matchNum) +
                ' rank matchs')
            print("Win rate:", str(int(winNum / matchNum * 100)) + "%")
            return
        else:
            print(name + '#' + tag,
                  ' has no recent rank match records')
            return

    def processMatchIds(self, matchIds, matchNum, name, tag, puuid, deckCodes, winNum):
        matchNum = 0
        for matchId in matchIds:
            try:
                # If match number bigger than MAX, getDetail will only ruturn data from cache
                detail = self.riot.getDetail(matchId, matchNum)
                if str(detail).isdigit():
                    print(
                        name + '#' + tag, 'Riot server [' + Models.network.API_KEY[-4:] + '] busy ' +
                        str(detail))
                    continue
                if detail is None:
                    continue
                print('detail', detail)
                gameMode = detail['info']['game_mode']
                gameType = detail['info']['game_type']
                startTime = detail['info']['game_start_time_utc']

                if gameMode in cs.UNSUPPORTED_MODE:
                    continue
                
                if gameType in cs.UNSUPPORTED_TYPE:
                    continue
                
                

                self.matchesJson.append(self.processMatchDetail(detail))
                matchNum += 1
                riotId = detail['metadata']['participants']
                outcome = None
                opponentDetail = None
                myDetails = None
                totalTurn = detail['info']['total_turn_count']
                myIndex = 1
                opponentIndex = 0
                if riotId[0] == puuid:
                    myIndex = 0
                    opponentIndex = 1
                else:
                    # differnet APIs has df puuid, has to double check if equal playernames when may using caching data
                    indexName = self.riot.getPlayerName(riotId[0])
                    if indexName[0].lower() == name.lower() and indexName[1].lower() == tag.lower():
                        myIndex = 0
                        opponentIndex = 1
                opName = self.riot.getPlayerName(riotId[opponentIndex])
                fullName = opName[0] + '#' + opName[1]
                opponentDetail = detail['info']['players'][opponentIndex]
                myDetails = detail['info']['players'][myIndex]
                outcome = myDetails["game_outcome"]
                if outcome == 'win':
                    winNum += 1
                print(detail)
                self.addMatchToSummary(
                    myDetails['deck_code'], outcome, utility.toLocalTimeString(startTime, True))
                deckCodes.append(myDetails['deck_code'])
                settingServer = self.riot.network.setting.getServer()
                rank = getRankStr(opName[0], settingServer)
                gameTypeString = '[' + gameType + ']'
                if gameType == '':
                    gameTypeString = ''
                print(fullName + ' ' + rank,
                        gameTypeString + ' [' + gameMode + '] ' +
                        utility.toLocalTimeString(startTime), outcome,
                        myDetails['deck_code'],
                        utility.getFactionString(myDetails["factions"]),
                        opponentDetail['deck_code'],
                        utility.getFactionString(opponentDetail["factions"]),
                        str(totalTurn) + ' Order of Play: ' + str(myDetails['order_of_play']), matchNum)
            except Exception as e:
                print('Read MatchId Error match id: ', matchId , e)
                continue
        return matchNum, winNum


    def processMatchDetail(self, detail):
        try:
            playerPuuids = detail['metadata']['participants']
        except Exception as e:
            #print('processMatchDetail error:', e)
            print('processMatchDetail error')
            return detail
        playernames = []
        player_info = []
        for puuid in playerPuuids:
            name, tag = self.riot.getPlayerName(puuid)
            rank, lp = checkRank(name, self.riot.network.setting.getServer())
            playernames.append(name + '#' + tag)
            player_info.append({'name':name, 'tag':tag, 'rank':rank, 'lp':lp})
        detail['playernames'] = playernames
        detail['player_info'] = player_info
        return detail