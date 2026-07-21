
```d2
Start: {shape: oval}
Loop Condition: {
  label: Is 'Exit' typed?
  shape: diamond
}
End: {shape: oval}
Game Logic: {shape: rectangle}

# 2. Define the Connections (The Logic)
Start -> Loop Condition

# If 'Yes', we break the loop
Loop Condition -> End: Yes

# If 'No', we run the game code
Loop Condition -> Game Logic: No
Game Logic -> Loop Condition: Update State & Repeat
```

```mermaid
graph TD
    Start([Player Enters Room]) --> CheckItem{Is there an item?}
    CheckItem -- No --> MoveOn[Ask for next move]
    CheckItem -- Yes --> HasItem{Is item already in inventory?}
    
    HasItem -- Yes --> Msg1[Print: You already have this.]
    HasItem -- No --> Action[Input: Do you want to take it?]
    
    Action -- "No" --> MoveOn
    Action -- "Yes" --> UpdateInv[Add item to List]
    UpdateInv --> RemoveItem[Remove item from Room Dictionary]
    RemoveItem --> MoveOn
```