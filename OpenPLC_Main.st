PROGRAM main
VAR
    StartButton AT %IX100.0 : BOOL;
    SafetyDoor AT %IX100.1 : BOOL;
    Box_Not_Waiting AT %IX100.2 : BOOL;
    Picker_Holding_Box AT %IX100.3 : BOOL;
    Picker_Rotating AT %IX100.4 : BOOL;
    Picker_Moving_Z AT %IX100.5 : BOOL;

    Conveyor_Move AT %QX100.0 : BOOL;
    Picker_Move_Down AT %QX100.1 : BOOL := FALSE;
    Picker_Grab AT %QX100.2 : BOOL := FALSE;
    Picker_Rotate_CCW AT %QX100.3 : BOOL := FALSE;
    Picker_Rotate_CW AT %QX100.4 : BOOL := FALSE;

    RUN : BOOL;
    BoxNotWaiting_Fall : F_TRIG;
    PickerHolding_Rise : R_TRIG;
    PickerMovingZ_Fall : F_TRIG;
    PickerRotating_Fall : F_TRIG;
END_VAR

BoxNotWaiting_Fall(CLK := Box_Not_Waiting);
PickerHolding_Rise(CLK := Picker_Holding_Box);
PickerMovingZ_Fall(CLK := Picker_Moving_Z);
PickerRotating_Fall(CLK := Picker_Rotating);

(* Rung 1: StartButton AND SafetyDoor energize RUN. *)
RUN := StartButton AND SafetyDoor;

(* Rung 2: RUN and a waiting box energize the conveyor. *)
Conveyor_Move := RUN AND Box_Not_Waiting;

(* Rung 3: falling edge of Box_Not_Waiting sets picker down and grab. *)
IF RUN AND BoxNotWaiting_Fall.Q AND NOT Picker_Holding_Box THEN
    Picker_Move_Down := TRUE;
    Picker_Grab := TRUE;
END_IF;

(* Rung 4: rising edge of Picker_Holding_Box resets picker down. *)
IF RUN AND PickerHolding_Rise.Q THEN
    Picker_Move_Down := FALSE;
END_IF;

(* Rung 5: falling edge of Z motion sets CCW and resets CW. *)
IF RUN AND PickerMovingZ_Fall.Q AND Picker_Holding_Box THEN
    Picker_Rotate_CCW := TRUE;
    Picker_Rotate_CW := FALSE;
END_IF;

(* Rung 6: falling edge of rotation resets grab and CCW, and sets CW. *)
IF RUN AND PickerRotating_Fall.Q AND Picker_Holding_Box THEN
    Picker_Grab := FALSE;
    Picker_Rotate_CW := TRUE;
    Picker_Rotate_CCW := FALSE;
END_IF;

END_PROGRAM
