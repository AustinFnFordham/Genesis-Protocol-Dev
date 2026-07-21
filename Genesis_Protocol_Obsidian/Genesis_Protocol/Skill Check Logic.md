
```d2
direction: down

# 1. DEFINE STYLES (Classes)
classes: {
  logic_step: {
    shape: rectangle
    style: {stroke-width: 2}
  }
  decision: {
    shape: diamond
    style: {stroke: "#f4a261"; stroke-width: 2}
  }
  end_state: {
    shape: oval
    style: {fill: "#264653"; stroke: transparent; font-color: white}
  }
}

# 2. SETUP PHASE
START: {shape: oval}

Setup Variables: {
  class: logic_step
  label: "SET current_room = 'Hangar Bay'\nSET inventory = []"
}

# FIXED: Changed shape to 'class' to allow data listing
Define Rooms Dictionary: {
  shape: class
  # Visualizing the Python Dictionary Keys
  Hangar Bay: "{North: Engineering, South: Crew Qtrs}"
  Engineering: "{South: Hangar Bay, Item: Hyperdrive}"
  Armory: "{Item: Blaster}"
  Bridge: "{Type: Boss Room}"
}

START -> Setup Variables
Setup Variables -> Define Rooms Dictionary

# 3. GAME LOOP
Loop Start: {shape: circle; label: "While\nActive"}
Define Rooms Dictionary -> Loop Start

Input Phase: {
  class: logic_step
  label: "1. Print Status\n2. READ player_input\n3. Split (Command, Direction)"
}

Loop Start -> Input Phase

# 4. LOGIC FORK
Command Check: {
  class: decision
  label: "Check Command"
}

Input Phase -> Command Check

# === PATH A: MOVEMENT (GO) ===
Command Check -> Valid Move?: {
  label: "if 'go'"
  class: decision
}

Valid Move? -> Update Room: {
  label: "Yes (Valid Exit)"
  class: logic_step
  tooltip: "current_room = new_room"
}
Valid Move? -> Invalid Move Msg: "No (Invalid Exit)"

# End Game Check
Update Room -> Is Bridge?: {class: decision}
Is Bridge? -> Loop Start: "No"

Is Bridge? -> Has 6 Items?: {
  label: "Yes (Boss)"
  class: decision
}

Has 6 Items? -> WIN: {
  label: "Yes"
  class: end_state
  label: "YOU WIN"
}
Has 6 Items? -> LOSE: {
  label: "No"
  class: end_state
  label: "GAME OVER"
}

# === PATH B: ITEM PICKUP (GET) ===
Command Check -> Item Exists?: {
  label: "if 'get'"
  class: decision
}

Item Exists? -> Update Inventory: {
  label: "Yes (Item in Room)"
  class: logic_step
  label: "1. inventory.append\n2. delete item from room"
}
Item Exists? -> Item Error Msg: "No"

# === LOOP BACKS ===
Invalid Move Msg -> Loop Start
Update Inventory -> Loop Start
Item Error Msg -> Loop Start
Command Check -> Loop Start: "Else (Invalid Cmd)"
```


