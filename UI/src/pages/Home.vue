<template>

    <div class="left-nav">
        <button class="left-nav-btn disabled"><span><i class="fas fa-user-circle"></i></span></button>
        <button class="left-nav-btn selected"><span><i class="fas fa-search"></i></span></button>
    </div>
    
    <base-window-controls :title="''" :titleType="'window'"></base-window-controls>
    
    <div class="content">
        <div class="history-content-container">
            <div class="region-tabs">
                <div class="region-option" 
                v-for="(region, index) in regions"
                :class="{selected: selectedRegion == region}" 
                :key="index"
                @click="selectRegion(region)">{{region}}</div>
            </div>
            <div class="search-bar-container">
                <input class="search-bar" 
                    @keyup="searchName" 
                    @keyup.enter="searchHistory"
                    @keyup.up="autoCompleteIndexMinus"
                    @keyup.down="autoCompleteIndexPlus"
                    v-model="searchText"/>
                <div class="search-bar-auto-complete">
                    <div class="auto-complete-item" 
                        v-for="(name, index) in inputNameList" :key="index" 
                        :class="{selected: autoCompleteIndex == index}"
                        @click="searchHistoryAutoComplete(index)"
                    >
                        {{name}}
                    </div>
                </div>
                <button class="search-btn" @click="searchHistory"><span><i class="fas fa-search"></i></span></button>
            </div>
            <div class="summary-container" v-if="!isLoading">
                <div class="player-summary">
                    <div class="name">{{playerName}}</div>
                    <!-- <div class="detail server">Server: SEA</div> -->
                    <div class="detail rank" v-if="playerRank">Rank: {{playerRank}}</div>
                    <div class="detail lp" v-if="playerLP">LP: {{playerLP}}</div>
                </div>
                <div class="history-summary">
                    <div class="win-loss">{{winloss}}</div>
                    <div class="winrate">{{winrate}}</div>
                </div>
                <!-- <div class="history-chart">
                    <div class="decks-filter">
                        <div class="deck-option">Lee Zoe</div>
                        <div class="deck-option">Azir Irelia</div>
                    </div>
                </div> -->
            </div>

            <div class="match-history-container" v-if="!isLoading">
                <match-history 
                    @show-deck="showDeck" v-for="(match, index) in matches" :key="index"
                    :opponentName="match.opponentName" 
                    :deck="match.deck"
                    :opponentDeck="match.opponentDeck"
                    :rounds="match.rounds"
                    :win="match.win"
                    :time="match.time"
                    :badges="match.badges"
                ></match-history>
                
            </div>

            <div class="loading-text" v-if="isLoading">Loading...</div>
        </div>
    </div>

    <div class="deck-content-container" :class="{hidden: !isShowDeck}">
        <div class="deck-content-top-bar">
            <button class="collapse-btn" @click="hideDeck"><span><i class="fas fa-chevron-right"></i></span></button>
            <deck-regions :deck="deckCode"></deck-regions>
        </div>
        <div class="deck-content-detail">
            <match-history-deck-detail :deck="deckCode"></match-history-deck-detail>
        </div>
    </div>

    <div class="bottom-bar">
        <div class="left">
            <!-- <div class="status">Status: Fine</div> -->
        </div>
        <div class="right">
            <div class="version">v0.9.7.2 Beta</div>
        </div>
    </div>
</template>

<script>

import BaseWindowControls from '../components/BaseWindowControls.vue'
import axios from 'axios'
import MatchHistory from '../components/MatchHistory.vue'
import DeckRegions from '../components/DeckRegions.vue'
import MatchHistoryDeckDetail from '../components/MatchHistoryDeckDetail.vue'

const requestDataWaitTime = 200 //ms
const inputNameListLength = 10;

const portNum = "63312"

let cancelToken

const regionNames = {
    'NA': 'americas',
    'EU': 'europe',
    'AS': 'asia',
}

function processDate(dateString) {
    var time
    var date = new Date(dateString)

    var milliElapsed = Date.now() - date
    var secondsElapsed = milliElapsed / 1000
    var minElapse = secondsElapsed / 60
    var hoursElapse = minElapse / 60
    var daysElapsed = hoursElapse / 24

    if (secondsElapsed < 60) {
        time = Math.floor(secondsElapsed) + " sec. ago"
    } else if (minElapse < 60) {
        time = Math.floor(minElapse) + " min. ago"
    } else if (hoursElapse < 24) {
        if (Math.floor(hoursElapse) == 1) {
            time = Math.floor(hoursElapse) + " hour ago"
        } else {
            time = Math.floor(hoursElapse) + " hours ago"
        }
    } else if (daysElapsed < 7) {
        if ( Math.floor(daysElapsed) == 1) {
            time = Math.floor(daysElapsed) + " day ago"
        } else {
            time = Math.floor(daysElapsed) + " days ago"
        }
    } else {
        time = date.toLocaleDateString()
    }

    return time
}

export default {
    mounted() {
        console.log("Mounted")
        var test = 'Hello'
    },
    data() {
        return {
            // rawDataString: null,
            deckCode: null,
            isShowDeck: false,
            matches: null,
            winloss: "",
            winrate: "",
            playerName: "",
            playerTag: "",
            playerRank: null,
            playerLP: null,
            searchText: "",
            isLoading: false,
            inputNameList: [],
            autoCompleteIndex: -1,
            regions: ["NA", "EU", "AS"],
            selectedRegion: "NA",
        }
    },
    computed: {
    },
    components: { 
        BaseWindowControls,
        MatchHistory,
        DeckRegions,
        MatchHistoryDeckDetail,
    },
    methods: {
        selectRegion(region) {
            this.selectedRegion = region
            this.searchName()
        },
        searchName() {
            // console.log("searchName")
            if (this.searchText.length > 0) {
                this.requestNameData()
            } else {
                this.resetInputNameList()
            }
        },
        resetInputNameList() {
            // console.log("resetList")
            this.inputNameList = []
            this.autoCompleteIndex = -1
        },
        autoCompleteIndexPlus() {
            this.autoCompleteIndex += 1
            if (this.autoCompleteIndex > inputNameListLength - 1) {
                this.autoCompleteIndex = inputNameListLength - 1
            }
        },
        autoCompleteIndexMinus() {
            this.autoCompleteIndex -= 1
            if (this.autoCompleteIndex < -1) {
                this.autoCompleteIndex = -1
            }
        },
        searchHistoryAutoComplete(index) {
            this.autoCompleteIndex = index
            this.searchHistory()
        },
        searchHistory() {
            if (this.inputNameList.length > 0 && this.inputNameList[this.autoCompleteIndex]) {
                this.searchText = this.inputNameList[this.autoCompleteIndex]
                document.querySelector(".search-bar").blur()
                this.resetInputNameList()
            }
            var splited = this.searchText.split("#")
            if (splited.length == 2 && splited[0].length > 0 && splited[1].length > 0) {
                this.playerName = splited[0]
                this.playerTag = splited[1]
                // console.log("Searching ", this.playerName, "#", this.playerTag)
                this.requestHistoryData()
            }
        },
        // requestDataAgain() {
        //     return new Promise(resolve => {
        //         setTimeout(() => {
        //             resolve('Requesting new Data')
        //         }, requestDataWaitTime);
        //     })
        // },
        clearInfo() {
            this.winloss = ""
            this.winrate = ""
            this.playerName = ""
            this.playerTag = ""
            this.playerRank = null
            this.playerLP = null
            this.matches = []
        },
        errorHistory() {
            this.clearInfo()
            this.playerName = "No history found"
        },
        processHistoryData(data) {
            this.matches = []
            this.playerRank = null
            this.playerLP = null
            var totalWins = 0
            var totalLoss = 0
            // var totalMatches = data.length

            // console.log(data)
            for (var key in data) {
                // console.log(data[key])

                if (!data[key]) continue // Skip if null history

                var isFirstPlayer = data[key].player_info[0].name.toLowerCase() == this.playerName.toLowerCase()
                
                var player, playerGame, opponent, opponentGame;
                var info = data[key].info
                
                var opponentName, deck, opponentDeck, rounds, win, time, order;
                
                if (isFirstPlayer) {
                    playerGame = info.players[0]
                    opponentGame = info.players[1]

                    player = data[key].player_info[0]
                    opponent = data[key].player_info[1]
                } else {
                    playerGame = info.players[1]
                    opponentGame = info.players[0]

                    player = data[key].player_info[1]
                    opponent = data[key].player_info[0]
                }

                if (!playerGame || !opponentGame || !player || !opponent) continue;

                this.playerName = player.name
                opponentName = opponent.name

                if (!this.playerRank) this.playerRank = player.rank
                if (!this.playerLP) this.playerLP = player.lp
                
                deck = playerGame.deck_code
                opponentDeck = opponentGame.deck_code
                order = playerGame.order_of_play
                win = playerGame.game_outcome == "win"
                if (win) {
                    totalWins += 1
                } else {
                    totalLoss += 1
                }
                rounds = info.total_turn_count
                var badges = []
                if (info.game_mode) badges.push(info.game_mode.replace(/([A-Z])/g, ' $1').trim().replace("Lobby", ""))
                if (info.game_type) badges.push(info.game_type.replace(/([A-Z])/g, ' $1').trim().replace("Lobby", ""))

                time = processDate(info.game_start_time_utc)

                this.matches.push({
                    opponentName: opponentName,
                    deck: deck,
                    opponentDeck: opponentDeck,
                    rounds: rounds,
                    win: win,
                    time: time,
                    badges: badges,
                })
            }
            // var totalLoss = totalMatches - totalWins;
            var totalMatches = totalLoss + totalWins;
            this.winloss = `${totalWins}W ${totalLoss}L`
            this.winrate = Math.floor(totalWins/totalMatches*100) + "% winrate"
        },
        async requestNameData() {
            
            axios.get(`http://127.0.0.1:${portNum}/name/${regionNames[this.selectedRegion]}/${this.searchText}`)
                .then((response) => {
                    if (response.data == "Error") {
                        // Error
                    } else {
                        // console.log(response.data)
                        if (document.querySelector(".search-bar") == document.activeElement) {
                            this.inputNameList = response.data.slice(0, inputNameListLength);
                        } else {
                            this.resetInputNameList()
                        }
                        
                    }
                })
                .catch((e) => {
                    if (axios.isCancel(e)) {
                        console.log("Request cancelled");
                    } else 
                    { console.log('error', e) }
                })
        },
        async requestHistoryData() {

            this.isLoading = true;
            this.inputNameList = [];

            //Check if there are any previous pending requests
            if (typeof cancelToken != typeof undefined) {
                cancelToken.cancel("Operation canceled due to new request.")
            }
            
            //Save the cancel token for the current request
            cancelToken = axios.CancelToken.source()

            axios.get(`http://127.0.0.1:${portNum}/search/${regionNames[this.selectedRegion]}/${this.playerName}/${this.playerTag}`,
                    { cancelToken: cancelToken.token }) // Pass the cancel token
                .then((response) => {
                    this.isLoading = false;

                    if (response.data == "Error") {
                        console.log("History Search Error")
                        this.errorHistory()
                    } else {
                        this.processHistoryData(response.data)
                    }
                })
                .catch((e) => {
                    if (axios.isCancel(e)) {
                        console.log("Request cancelled");
                    } else 
                    { console.log('error', e) }
                })

        },
        showDeck(deck) {
            // console.log("Main Show Deck", deck)
            if (this.deckCode == deck && this.isShowDeck == true) {
                this.isShowDeck = false
            } else {
                this.deckCode = deck
                this.isShowDeck = true
            }
            
        },
        hideDeck() {
            this.isShowDeck = false
        },
    },

}

</script>

<style scoped>

    .region-tabs {
        display: flex;

        gap: 5px;
    }

    .region-option {
        
        color: #ABABAB;
        cursor: pointer;

        width: 56px;
        height: 30px;

        line-height: 30px;

        border: 1px solid #ABABAB;
        border-radius: 4px 4px 0px 0px;

        align-items: center;
        text-align: center;
        vertical-align: middle;
    }

    .region-option:hover {
        color: white;
    }

    .region-option.selected {
        cursor: default;
        color: var(--col-background);
        background:white;
        border: 1px solid white;
        border-radius: 4px 4px 0px 0px;
    }

    .search-bar-container {
        width: 100%;
        display: flex;
        flex-wrap: nowrap;

        position: relative;
    }

    .search-bar {
        width: 100%;
        height: 36px;

        color: white;
        font-size: 20px;

        border: 1px solid #FFFFFF;
        box-sizing: border-box;
        border-radius: 0px 4px 4px 4px;

        background: var(--col-background);
    }

    .search-bar:focus {
        outline: 0px;
        background: var(--col-dark-grey);
    }

    .search-bar-auto-complete {
        position: absolute;
        top: 36px;
        left: 0;
        text-align: left;
        background: var(--col-background);
        padding: 5px 0px 0px 0px;

        z-index: 2;
    }

    .auto-complete-item {
        padding: 5px 15px 5px 5px;
        cursor: pointer;
    }

    .auto-complete-item:hover, .auto-complete-item.selected {
        background: var(--col-dark-grey);
    }

    .search-btn {
        color: white;
        background: none;
        outline: 0px;
        border: 0px;
        cursor: pointer;
        width: 6%;
        text-align: right;
    }

    .summary-container {
        margin: 20px 0px;
        display: flex;
        gap: 10px;
        justify-content: space-between;
        align-items: center;
    }

    .match-history-container {
        height: calc(100vh - 306px);
        overflow: scroll;
    }

    .loading-text {
        font-size: 24px;
        margin: 20px 0px;
    }

    .player-summary {
        text-align: left;
    }

    .player-summary .name {
        font-size: 24px;
        margin-bottom: 5px;
    }

    .player-summary .detail {
        font-size: 12px;
        color: var(--col-lighter-grey);
    }

    .history-summary {
        font-size: 24px;
        /* margin-left: 20px; */
        text-align: right;
    }

    .history-summary .winrate {
        font-size: 18px;
        color: var(--col-lighter-grey);
    }

    .content {
        text-align: center;
        display: block;
        width: calc(100% - 80px);
        min-width: 500px;
        margin-left: 80px;
        margin-top: 43px;
        padding: 10px 40px;
        box-sizing: border-box;
        white-space: normal;
        color: white;
    }

    .deck-content-container {
        display: block;
        position: fixed;
        width: 250px;
        height: calc(100vh - 88px);
        top: 0px;
        right: 0px;

        margin-top: 43px;

        background: var(--col-background);
        /* overflow: scroll; */

        transition: right 0.2s ease;
    }

    .deck-content-container.hidden {
        right: -250px;

    }

    /* .deck-content-top-bar {
        display: flex;
    } */

    .collapse-btn {
        display: block;
        position: absolute;
        
        width: 40px;
        height: 50px;

        background: none;
        outline: 0px;
        border: 0px;
        color: white;

        cursor: pointer;
    }

    .deck-content-detail {
        height: calc(100vh - 138px);
    }

    .history-content-container {
        margin: auto;
        max-width: 550px;
    }

    .left-nav {
        position: absolute;
        top: 0;
        left: 0;
        width: 80px;
        height: 100vh;
        background: #282828;
        z-index: 5;
        display: flex;
        flex-direction: column;

        gap: 10px;

        padding-top: 80px;

        box-sizing: border-box;

    }

    .left-nav-btn {
        height: 50px;
        font-size: 24px;
        color: var(--col-gold);
        background: none;
        border: 0px;
        cursor: pointer;
    }

    .left-nav-btn:focus {
        outline: 0px;
    }

    .left-nav-btn.selected {
        color: white;
        cursor: default;
    }

    .left-nav-btn.disabled {
        color: var(--col-grey);
        cursor: default;
    }



    .bottom-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100vw;
        height: 45px;
        background: #383838;
        z-index: 6;

        display: flex;
        justify-content: space-between;
        align-items: center;

        color: white;
    }

    .bottom-bar .left, .bottom-bar .right {
        padding: 20px;
    }

</style>