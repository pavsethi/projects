"use strict";

const PLAYER_X = "X";
const PLAYER_O = "O";
const EMPTY = "";

var app = {};
app.config = {}
app.config.data = function() {
    return {
        board: Vue.ref([["", "", ""], ["", "", ""], ["", "", ""]]),
        gameOver: false,
    }
}

app.config.methods = {};

app.config.methods.setPlayerMove = function(rowIndex, cellIndex){
    //check that game is not over
    console.log("player move");
    console.log(this.gameOver);
    if (!this.gameOver && this.board[rowIndex][cellIndex] === EMPTY){
        console.log("setting player move");
        this.board[rowIndex][cellIndex] = PLAYER_X;
        // check that player has not won or tied
        console.log("checking win", this.checkWin());
        console.log("checking draw:", this.checkDraw());
        let res = this.checkWin();
        if (!res[0] && !this.checkDraw()){
            this.computeComputerMove();
        } else {
            this.gameOver = true;
        }
    }
}

app.config.methods.computeComputerMove = function() {
    let bestScore = -Infinity;
    let move = [];
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
            if (this.board[i][j] === EMPTY) {
                this.board[i][j] = PLAYER_O;
                let score = this.minimax(this.board, 0, false);
                this.board[i][j] = EMPTY;
                if (score > bestScore) {        // computer wants to maximize score to win
                    bestScore = score;
                    move = [i, j];
                }
            }
        }
    }
    console.log(move);
    this.board[move[0]][move[1]] = PLAYER_O;
    let res = this.checkWin()
    if (res[0]) {
        console.log("changing game over state");
        this.gameOver = true;
    }
    console.log("checking win", res[0]);
}

app.config.methods.checkWin = function() {
    // check if horizontal win or vertical win
    for(let i = 0; i < 3; i++) {
        if (this.board[i][0] !== EMPTY && this.board[i][0] === this.board[i][1] && this.board[i][1] === this.board[i][2]){
            console.log("horizontal win");
            //this.gameOver = true;
            return [true, this.board[i][0]];
        } else if (this.board[0][i] !== EMPTY && this.board[0][i] === this.board[1][i] && this.board[1][i] === this.board[2][i]){
            console.log("vertical win");
            //this.gameOver = true;
            return [true, this.board[0][i]];
        }
    }

    // check if diagonal win
    if (this.board[0][0] !== EMPTY && this.board[0][0] === this.board[1][1] && this.board[1][1] === this.board[2][2]) {
        console.log("diagonal win");
        //this.gameOver = true;
        return [true, this.board[0][0]];
    }
    if (this.board[0][2] !== EMPTY && this.board[0][2] === this.board[1][1] && this.board[1][1] === this.board[2][0]) {
        console.log("diagonal win");
        //this.gameOver = true;
        return [true, this.board[0][2]];
    }
    return [false, ""];
}

app.config.methods.checkDraw = function() {
    for (let x = 0; x < 3; x++) {
        for (let y = 0; y < 3; y++) {
            if (this.board[x][y] == EMPTY) {
                return false;
            }
        }
    }

    return true;
}

app.config.methods.resetGame = function() {
    this.board = [["", "", ""], ["", "", ""], ["", "", ""]];
    this.gameOver= false;
}

app.config.methods.minimax = function(board, depth, isMaximizing) {
    let res = this.checkWin();
    if (res[0]) {
        if (res[1] === "O") {
            return 10;
        } else if (res[1] === "X") {
            return -10;
        }
    } else if (this.checkDraw()) {
        return 0;
    }

    //CITE: TA Mrinal 
    if (isMaximizing) {
        let maxEval = -Infinity;
        //iterate through each cell
        for (let i = 0; i < board.length; i++) {
            for (let j = 0; j < board[i].length; j++) {
                if (board[i][j] === EMPTY) {
                    board[i][j] = PLAYER_O;
                    maxEval = Math.max(maxEval, this.minimax(board, depth + 1, false));     // calculate score with potential move
                    board[i][j] = EMPTY;
                }
            }
        }
        return maxEval;
    } else {
        let minEval = Infinity;
        for (let i = 0; i < this.board.length; i++) {
            for (let j = 0; j < this.board.length; j++) {
                if (board[i][j] == EMPTY) {
                    board[i][j] = PLAYER_X;
                    minEval = Math.min(minEval, this.minimax(board, depth + 1, true));
                    board[i][j] = EMPTY;
                }
            }
        }
        return minEval;
    }

};

app.vue = Vue.createApp(app.config).mount("#myapp");