import requests
from requests import models
from Models import setting
from Models.setting import Server
import constants as cs
import Models.utility as utility
import Models.process
from Models.leaderboard import getRankStr, updateLeaderboard
from Models.deck import getDeckCode
from Models.process import updateTrackServer
from Models.leaderboard import checkRank
import json

class Local:
    def __init__(self, setting):
        
        self.opponentName = None
        self.opponentTag = None
        self.isClientRuning = False
        self.isInProgress = False
        self.setting = setting
        self.playernames = set()
        self.playername = None
        self.trackerDict = {}
        self.session = requests.Session()
        self.handCount = 0
        self.playedCards = {}
        self.graveyard = {}
        self.opGraveyard = {}
        self.myGraveyard = {}
        self.positional_rectangles = None
        self.static_decklist = None
        self.trackJson = {}
        self.updatePlayernames()

    # call this function after changes server in the tracker
    def reset(self):
        self.opponentName = None
        self.playername = None
        self.opponentTag = None
        self.isClientRuning = False
        self.isInProgress = False
        self.playedCards = {}
        self.graveyard = {}
        self.opGraveyard = {}
        self.trackJson = {}
        #self.positional_rectangles = None
        self.trackerDict = {}

    def updateTracker(self, rectangles):
        if rectangles is None:
            return
        self.handCount = 0
        for card in rectangles:
            if card['LocalPlayer'] is True:
                self.playedCards[card['CardID']] = card['CardCode']
            else:
                self.graveyard[card['CardID']] = card['CardCode']
            if card['TopLeftY'] - card['Height'] < 10:
                self.handCount += 1
        # have to know if player have changed cards
        if len(self.playedCards) == 5 and len(self.graveyard) == 1:
            self.playedCards = {}
            self.graveyard = {}

    def updateLeftCards(self, currentCards):
        if currentCards is None:
            return
        for key in self.playedCards:
            cardCode = self.playedCards[key]
            if cardCode in currentCards:
                num = currentCards[cardCode]
                if num > 0:
                    num -= 1
                currentCards[cardCode] = num
                if num == 0:
                    del currentCards[cardCode]
        return {x:y for x,y in currentCards.items() if y!=0}

    def updateOpGraveyard(self):
        self.opGraveyard = {}
        for key in self.graveyard:
            cardCode = self.graveyard[key]
            if cardCode in self.opGraveyard:
                self.opGraveyard[cardCode] += 1
            else:
                self.opGraveyard[cardCode] = 1
        if 'face' in self.opGraveyard:
            del self.opGraveyard['face']

    def updateMyGraveyard(self):
        rectangles = self.positional_rectangles['Rectangles']
        if rectangles is None:
            return
        self.myGraveyard = {}
        myGraveyardWithId = self.playedCards.copy()
        if self.playedCards == {}:
            return
        for card in rectangles:
            if card['LocalPlayer'] is True:
                del myGraveyardWithId[card['CardID']]
        for key in myGraveyardWithId:
            cardCode = myGraveyardWithId[key]
            if cardCode in self.myGraveyard:
                self.myGraveyard[cardCode] += 1
            else:
                self.myGraveyard[cardCode] = 1
        if 'face' in self.myGraveyard:
            del self.myGraveyard['face']

    def playedCardsToDeck(self):
        myPlayedCards = {}
        for cardCode, key in self.playedCards.items():
            if cardCode in myPlayedCards:
                myPlayedCards[key] += 1
            else:
                myPlayedCards[key] = 1
        if 'face' in myPlayedCards:
            del myPlayedCards['face']
        return myPlayedCards

    def updateMyDeck(self):
        try:
            localDeckRequest = self.session.get(self.getLocalDeckLink())
            details = localDeckRequest.json()
        except Exception as e:
            print('updateMyDeck Error: ', e)
            return
        if details['DeckCode'] is None:
            print('updateMyDeck Match is not start')
            return
        currentCards = details['CardsInDeck']
        currentCards = self.updateLeftCards(currentCards)
        currentDeckCode = getDeckCode(currentCards)
        self.trackerDict['deckCode'] = details['DeckCode']
        self.trackerDict['cardsInDeck'] = details['CardsInDeck']
        self.trackerDict['currentDeckCode'] = currentDeckCode
        self.updateOpGraveyard()
        self.trackerDict['opGraveyard'] = self.opGraveyard
        self.trackerDict['opGraveyardCode'] = getDeckCode(self.opGraveyard)
        self.updateMyGraveyard()
        self.trackerDict['myGraveyard'] = self.myGraveyard
        self.trackerDict['myGraveyardCode'] = getDeckCode(self.myGraveyard)
        self.trackerDict['myPlayedCards'] = self.playedCardsToDeck()
        self.trackerDict['myPlayedCardsCode'] = getDeckCode(self.trackerDict['myPlayedCards'])
        # print(self.trackerDict)

    def updateStatusFlask(self):
        #Models.process.getPort(self.setting)
        try:
            localRequest = self.session.get(self.getLocalLink())
            self.positional_rectangles = localRequest.json()
        except Exception as e:
            print('client is not running: ', e)
            self.reset()
            return {}
        if self.positional_rectangles['GameState'] == 'InProgress':
            self.updateTracker(self.positional_rectangles['Rectangles'])
            self.updateMyDeck()
            print(self.trackerDict)
        else:
            self.reset()
            self.trackJson
            self.trackJson['positional_rectangles'] = self.positional_rectangles
            return self.trackJson

        self.trackJson['hand_size'] = self.handCount
        self.trackJson['positional_rectangles'] = self.positional_rectangles
        self.trackJson['deck_tracker'] = self.trackerDict
        
        opInfo = {}
        #updateTrackServer(self.setting)
        self.updateTagByName(self.positional_rectangles['OpponentName'])
        opInfo['name'] = self.positional_rectangles['OpponentName']
        opInfo['tag'] = self.opponentTag
        opInfo['rank'], opInfo['lp'] = checkRank(self.positional_rectangles['OpponentName'], self.setting.riotServer)
        self.trackJson['opponent_info'] = opInfo

        return self.trackJson


    def updateStatus(self, checkOpponent, showMessage, showStatus, showMatchs,
                     showDecks):
        Models.process.getPort(self.setting)
        try:
            localRequest = self.session.get(self.getLocalLink())
            if not self.isClientRuning:
                # LoR client launched
                print('LoR客户端已启动', '当前服务器:', self.setting.getServer())
                showStatus('[LoR Connected: ' + self.setting.getServer() + ']')
                self.isClientRuning = True
        except requests.exceptions.RequestException:
            if self.isClientRuning:
                print('LoR客户端已关闭')  # LoR client exited
                showStatus('[LoR Disconnected]')
                self.isClientRuning = False
                self.reset()
            return
        try:
            details = localRequest.json()
        except Exception as e:
            print('Decoding local port json failed: ', e)
            return
        self.positional_rectangles = details
        self.updateTracker(details['Rectangles'])
        gameState = details['GameState']
        vsPlayerStr = ''
        if gameState == 'InProgress':
            if not self.isInProgress:
                print('新对局开始')  # New Match Found
                self.isInProgress = True
            opName = details['OpponentName']
            playerName = details['PlayerName']
            if opName:
                if opName != self.opponentName:
                    if not playerName:
                        return
                    vsPlayerStr = getRankStr(opName.strip(
                    ), self.setting.getServer()) + ' vs ' + playerName.strip()
                    showStatus(
                        opName + ' ' + vsPlayerStr + ' ' +
                        getRankStr(playerName, self.setting.getServer()))

                    self.opponentName = opName
                    self.updateTagByName(self.opponentName)
                    showMessage(
                        opName + ' ' + vsPlayerStr + ' ' +
                        getRankStr(playerName, self.setting.getServer()))
                    if self.opponentTag is None:
                        # Play Tag does not exist
                        print('玩家姓名：', self.opponentName, '，无法找到Tag')
                        showMessage('Cannot find opponent tag')
                        showMessage('')
                        return
                    else:
                        # Opponent tag found:
                        print('发现对手：', self.opponentName, '#',
                              self.opponentTag, "正在载入卡组...")
                        showMessage(self.opponentName + '#' + self.opponentTag)
                        checkOpponent(self.opponentName, self.opponentTag,
                                      showMessage, showMatchs, showDecks)
        else:
            if self.isInProgress:
                if None not in (self.opponentName, self.opponentTag):
                    print(self.opponentName, '#', self.opponentTag, ' 对局结束')
                    # showMessage(self.opponentName + '#' + self.opponentTag + ' match finished')
                    showMessage('')
                self.reset()
                showStatus('LoR Connected: ' + self.setting.getServer())
                updateLeaderboard()

    def updateTagByName(self, name):
        try:        
            with open('data/' + self.setting.getServer() + '.json', 'r', encoding='utf-8') as fp:
                names = json.load(fp)
                if name in names:
                    self.opponentTag = names[name]
                    return
            with open(('Resource/' + self.setting.getServer() + '.dat'), 'r', encoding="utf-8") as search:
                for line in search:
                    fullName = line.rstrip().split('#')
                    if name == fullName[0]:
                        # print(fullName)
                        self.opponentTag = fullName[1]
                        return
        except Exception as e:
            print('updateTagByName', e)
        self.opponentTag = None

    def updatePlayernames(self):
        try: 
            self.playernames = set()
            with open('data/' + self.setting.getServer() + '.json', 'r', encoding='utf-8') as fp:
                names = json.load(fp)
                for name in names.items():
                    try:
                        self.playernames.add(name[0] + '#' + name[1])
                    except Exception as e:
                        print('updatePlayernames for loop playname:', name , e)
        except Exception as e:
            print('updatePlayernames', e)

            
        # with open(('Resource/' + self.setting.getServer() + '.dat'),
        #           encoding="utf8") as search:
        #     for line in search:
        #         fullName = line.strip()
        #         self.playernames.add(fullName)

    def getLocalLink(self):
        return cs.IP_KEY + self.setting.getPort() + cs.LOCAL_MATCH

    def getLocalDeckLink(self):
        return cs.IP_KEY + self.setting.getPort() + cs.LOCAL_DECK

    def getPlayerTag(self, name, serverName):
        try:        
            with open('data/' + serverName + '.json', 'r', encoding='utf-8') as fp:
                names = json.load(fp)
                if name in names:
                    return names[name]
        except Exception as e:
            print('updateTagByName', e)
        return ''    
