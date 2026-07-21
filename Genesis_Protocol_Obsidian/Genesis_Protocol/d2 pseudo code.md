```d2
direction: down

# --- STYLING ---
classes: {
  process: {
    shape: rectangle
    style: {
      fill: "#f0f4f8"
      stroke: "#334e68"
      stroke-width: 2
    }
  }
  decision: {
    shape: diamond
    style: {
      fill: "#ffe8cc"
      stroke: "#d9730d"
    }
  }
  io: {
    shape: parallelogram
    style: {
      fill: "#def7ec"
      stroke: "#03543f"
    }
  }
  start_end: {
    shape: oval
    style: {
      fill: "#333333"
      stroke: "#000000"
      font-color: white
    }
  }
}

# --- NODES & FLOW ---

Start: Start
Start.class: start_end

# Phase 1: Setup
Variables: Initialize Variables\n(lower=0, upper=0, secret=0, guess=0)
Variables.class: process

Start -> Variables

# Input Validation Loop
ValidBounds?: Valid Range?
ValidBounds?.class: decision

InputBounds: Input Lower & Upper Bounds
InputBounds.class: io

ErrorBounds: Print Error:\n"Lower must be < Upper"
ErrorBounds.class: io

Variables -> ValidBounds?
ValidBounds? -> InputBounds: No (Start Loop)
InputBounds -> CheckBounds: Check: lower < upper?
CheckBounds.class: decision

CheckBounds -> ErrorBounds: False
ErrorBounds -> InputBounds: Retry

CheckBounds -> GenSecret: True (Exit Loop)

# Phase 2: Game Init
GenSecret: Generate Secret Number\nRANDOM(lower, upper)
GenSecret.class: process

OutputRange: Print: "I'm thinking of a number..."
OutputRange.class: io

GenSecret -> OutputRange

# Phase 3: Main Game Loop
GuessLoop: Guess != Secret?
GuessLoop.class: decision

OutputRange -> GuessLoop

InputGuess: Input Guess
InputGuess.class: io

GuessLoop -> InputGuess: True (Continue)

RangeCheck: Guess in Range?\n(lower <= guess <= upper)
RangeCheck.class: decision

InputGuess -> RangeCheck

ErrorRange: Print Error:\n"Guess out of bounds"
ErrorRange.class: io

RangeCheck -> ErrorRange: No
ErrorRange -> GuessLoop

# Logic inside loop
CompareGuess: Compare Guess
CompareGuess.class: decision

RangeCheck -> CompareGuess: Yes

TooLow: Print "Too Low"
TooLow.class: io

TooHigh: Print "Too High"
TooHigh.class: io

Correct: Print "You got it!"
Correct.class: io

CompareGuess -> TooLow: guess < secret
CompareGuess -> TooHigh: guess > secret
CompareGuess -> Correct: guess == secret

TooLow -> GuessLoop
TooHigh -> GuessLoop

# End Game
EndGame: Thanks for Playing!
EndGame.class: io

End: End
End.class: start_end

Correct -> EndGame
# The loop condition technically breaks when correct, leading to end
GuessLoop -> EndGame: False (Solved)
EndGame -> End
```
